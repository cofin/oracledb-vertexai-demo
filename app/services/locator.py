"""A scalable, auto-wiring Service Locator for dependency injection."""

from __future__ import annotations

import inspect
from typing import Any, TypeVar, get_type_hints

from sqlspec.driver import AsyncDriverAdapterBase

from app.services.vertex_ai import VertexAIService

T = TypeVar("T")


class ServiceLocator:
    """A scalable service locator that uses introspection to automatically
    resolve and inject dependencies based on type hints.
    """

    def __init__(self) -> None:
        """Initializes the service locator."""
        self._cache: dict[type, Any] = {}
        self._singletons: set[type] = {VertexAIService}

    def get(self, service_cls: type[T], session: AsyncDriverAdapterBase | None) -> T:
        """Get an instance of a service, resolving its dependencies automatically.

        Args:
            service_cls: The class of the service to instantiate.
            session: The active database session, required for services
                     that interact with the database.

        Returns:
            An instance of the requested service.
        """
        # Import here to avoid circular imports
        from app.services.adk.tool_service import AgentToolsService
        from app.services.intent import IntentService

        # 1. Handle Singletons: If the class is marked as a singleton,
        # return a cached instance or create and cache it.
        if service_cls in self._singletons:
            if service_cls not in self._cache:
                # Singletons are created without a session.
                self._cache[service_cls] = self._create_instance(service_cls, None)
            return self._cache[service_cls]  # type: ignore[return-value]

        # 2. Handle complex services with special dependency injection needs
        if service_cls == IntentService:
            from app.services.exemplar import ExemplarService

            return IntentService(  # type: ignore[return-value]
                driver=session,
                exemplar_service=self.get(ExemplarService, session),
                vertex_ai_service=self.get(VertexAIService, session),
            )

        # Special handling for VertexAIService to inject CacheService
        if service_cls == VertexAIService:
            from app.services.cache import CacheService

            # Create VertexAI service with cache service
            cache_service = self.get(CacheService, session) if session else None
            return VertexAIService(cache_service=cache_service)  # type: ignore[return-value]

        if service_cls == AgentToolsService:
            from app.services.metrics import MetricsService
            from app.services.product import ProductService
            from app.services.store import StoreService

            return AgentToolsService(  # type: ignore[return-value]
                driver=session,
                product_service=self.get(ProductService, session),
                metrics_service=self.get(MetricsService, session),
                intent_service=self.get(IntentService, session),
                vertex_ai_service=self.get(VertexAIService, session),
                store_service=self.get(StoreService, session),
            )

        # 3. Handle Transient (session-scoped) services.
        if session is None:
            service_name = service_cls.__name__
            msg = f"A database session is required to create a transient instance of {service_name}"
            raise ValueError(msg)

        return self._create_instance(service_cls, session)

    def _create_instance(
        self,
        service_cls: type[T],
        session: AsyncDriverAdapterBase | None,
    ) -> T:
        """Creates an instance of a class by inspecting its __init__ method
        and recursively resolving dependencies.
        """
        # Get the constructor signature
        try:
            signature = inspect.signature(service_cls.__init__)
        except (TypeError, ValueError):
            return service_cls()

        # Get resolved type hints to handle forward references and string annotations
        type_hints = get_type_hints(service_cls.__init__)

        dependencies: dict[str, Any] = {}
        # Iterate over constructor parameters, skipping 'self'
        for param in list(signature.parameters.values())[1:]:
            param_type = type_hints.get(param.name, param.annotation)

            if param_type is inspect.Parameter.empty:
                msg = (
                    f"Cannot resolve dependency for '{service_cls.__name__}': "
                    f"Parameter '{param.name}' is missing a type hint."
                )
                raise TypeError(msg)

            # 3. Inject the database session/driver if type-hinted
            if (isinstance(param_type, type) and issubclass(param_type, AsyncDriverAdapterBase)) or param.name in (
                "driver",
                "session",
            ):
                dependencies[param.name] = session

            # 4. Skip parameters with default values (like object | None = None)
            elif param.default is not inspect.Parameter.empty:
                # Parameter has a default value, skip it
                continue

            # 5. Recursively resolve other service dependencies
            else:
                dependencies[param.name] = self.get(param_type, session)

        # 5. Create and return the instance with resolved dependencies
        return service_cls(**dependencies)
