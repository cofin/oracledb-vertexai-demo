# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Domain auto-discovery plugin for Litestar.

This plugin automatically discovers and registers controllers from domain packages,
eliminating the need for manual controller registration in ApplicationCore.

Discovery Pattern:
    The plugin scans domain packages (e.g., app.domain.*) for controller submodules:
    - controllers/ subpackage
    - routes/ subpackage
    - controller.py or controllers.py files
    - route.py or routes.py files

    Controllers are identified as subclasses of litestar.Controller defined in those modules.
"""

import importlib
import inspect
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from litestar import Controller
from litestar.events import EventListener

from app.lib.di import LitestarRouter

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

logger = structlog.get_logger()


@dataclass
class DomainPluginConfig:
    """Configuration for domain auto-discovery plugin."""

    domain_packages: list[str] = field(default_factory=lambda: ["app.domain"])
    discover_controllers: bool = True
    discover_listeners: bool = True
    controller_submodules: list[str] = field(default_factory=lambda: ["controllers", "routes", "controller", "route"])
    listener_submodules: list[str] = field(default_factory=lambda: ["events", "listeners"])
    use_dishka_router: bool = True
    log_discovered: bool = True


def find_controllers_in_module(module: object) -> list[type[Controller]]:
    """Find all Controller subclasses defined in a module."""
    controllers: list[type[Controller]] = []
    module_name = getattr(module, "__name__", "")

    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj is Controller:
            continue
        if not issubclass(obj, Controller):
            continue
        if getattr(obj, "__module__", None) != module_name:
            continue
        if name.startswith("_"):
            continue

        controllers.append(obj)

    return controllers


def find_listeners_in_module(module: object) -> list[EventListener]:
    """Find all event listeners defined in a module."""
    listeners: list[EventListener] = []

    for _, obj in inspect.getmembers(module):
        if isinstance(obj, EventListener):
            listeners.append(obj)

    return listeners


def discover_domain_controllers(
    domain_packages: list[str], controller_submodules: list[str] | None = None
) -> list[type[Controller]]:
    """Discover controllers in domain subpackages."""
    if _cache.is_cached(domain_packages):
        cached = _cache.get()
        if cached is not None:
            return cached

    if controller_submodules is None:
        controller_submodules = ["controllers", "routes", "controller", "route"]

    all_controllers: list[type[Controller]] = []

    for domain_pkg in domain_packages:
        for domain_module_path, _ in _iter_domain_directories(domain_pkg):
            for submodule_name in controller_submodules:
                controller_path = f"{domain_module_path}.{submodule_name}"
                controllers = _discover_controllers_in_submodule(controller_path)
                all_controllers.extend(controllers)

    seen: set[type[Controller]] = set()
    unique_controllers: list[type[Controller]] = []
    for ctrl in all_controllers:
        if ctrl not in seen:
            seen.add(ctrl)
            unique_controllers.append(ctrl)

    _cache.set(unique_controllers, domain_packages)

    return unique_controllers


def discover_domain_listeners(
    domain_packages: list[str], listener_submodules: list[str] | None = None
) -> list["EventListener"]:
    """Discover listeners in domain subpackages."""
    if listener_submodules is None:
        listener_submodules = ["events", "listeners"]

    all_listeners: list[EventListener] = []

    for domain_pkg in domain_packages:
        for domain_module_path, _ in _iter_domain_directories(domain_pkg):
            for submodule_name in listener_submodules:
                listener_path = f"{domain_module_path}.{submodule_name}"
                listeners = _discover_listeners_in_submodule(listener_path)
                all_listeners.extend(listeners)

    return all_listeners


class DomainPlugin:
    """Litestar plugin for automatic domain discovery."""

    __slots__ = ("config",)

    def __init__(self, config: DomainPluginConfig | None = None) -> None:
        """Initialize the domain plugin."""
        self.config = config or DomainPluginConfig()

    def on_app_init(self, app_config: "AppConfig") -> "AppConfig":
        """Initialize the plugin when app is created."""
        if self.config.discover_controllers:
            self._discover_and_register_controllers(app_config)

        if self.config.discover_listeners:
            self._discover_and_register_listeners(app_config)

        if self.config.log_discovered:
            app_config.on_startup = app_config.on_startup or []
            app_config.on_startup.insert(0, _on_startup_log_discovery)

        return app_config

    def _discover_and_register_controllers(self, app_config: "AppConfig") -> None:
        """Discover controllers and register them with the application."""
        controllers = discover_domain_controllers(self.config.domain_packages, self.config.controller_submodules)

        if not controllers:
            logger.warning("No controllers discovered", domain_packages=self.config.domain_packages)
            return

        self._store_controller_results(controllers)

        if self.config.use_dishka_router:
            router = LitestarRouter(path="/", route_handlers=controllers)
            app_config.route_handlers.append(router)
        else:
            app_config.route_handlers.extend(controllers)

    def _discover_and_register_listeners(self, app_config: "AppConfig") -> None:
        """Discover listeners and register them with the application."""
        listeners = discover_domain_listeners(self.config.domain_packages, self.config.listener_submodules)

        if not listeners:
            return

        _DiscoveryState.listener_count = len(listeners)

        app_config.listeners.extend(listeners)

    def _store_controller_results(self, controllers: list[type[Controller]]) -> None:
        """Store controller discovery results for deferred logging."""
        by_domain: dict[str, list[str]] = {}
        for ctrl in controllers:
            module = getattr(ctrl, "__module__", "unknown")
            parts = module.split(".")
            domain = parts[2] if len(parts) >= 3 and parts[1] == "domain" else "unknown"  # noqa: PLR2004

            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(ctrl.__name__)

        _DiscoveryState.controller_count = len(controllers)
        _DiscoveryState.controllers_by_domain = by_domain


async def _on_startup_log_discovery() -> None:  # noqa: RUF029
    """Lifespan startup hook to log discovery results after server header."""
    _DiscoveryState.log_discovery_results()


def clear_discovery_cache() -> None:
    """Clear the controller discovery cache and reset logging flags."""
    _cache.clear()
    _DiscoveryState.reset()


class _DiscoveryCache:
    """Cache for discovered controllers to avoid re-discovery."""

    def __init__(self) -> None:
        self.controllers: list[type[Controller]] | None = None
        self.packages: frozenset[str] | None = None

    def clear(self) -> None:
        """Clear the cache."""
        self.controllers = None
        self.packages = None

    def is_cached(self, domain_packages: list[str]) -> bool:
        """Check if results for these packages are cached."""
        return self.controllers is not None and self.packages == frozenset(domain_packages)

    def get(self) -> list[type[Controller]] | None:
        """Get cached controllers."""
        return self.controllers

    def set(self, controllers: list[type[Controller]], packages: list[str]) -> None:
        """Set cached controllers."""
        self.controllers = controllers
        self.packages = frozenset(packages)


_cache = _DiscoveryCache()


class _DiscoveryState:
    """Store discovery results for deferred logging during lifespan startup."""

    controller_count: int = 0
    controllers_by_domain: dict[str, list[str]] = {}
    listener_count: int = 0
    logged_controllers: bool = False
    logged_listeners: bool = False

    @classmethod
    def reset(cls) -> None:
        """Reset discovery state (for testing)."""
        cls.controller_count = 0
        cls.controllers_by_domain = {}
        cls.listener_count = 0
        cls.logged_controllers = False
        cls.logged_listeners = False

    @classmethod
    def log_discovery_results(cls) -> None:
        """Log discovery results (called during lifespan startup)."""
        if not cls.logged_controllers and cls.controller_count > 0:
            cls.logged_controllers = True
            logger.info("Loaded API controllers", total=cls.controller_count, domains=len(cls.controllers_by_domain))
            logger.debug(
                "Controller inventory by domain",
                by_domain={k: sorted(v) for k, v in sorted(cls.controllers_by_domain.items())},
            )

        if not cls.logged_listeners and cls.listener_count > 0:
            cls.logged_listeners = True
            logger.info("Discovered domain listeners", total=cls.listener_count)


def _iter_domain_directories(domain_pkg: str) -> list[tuple[str, Path]]:
    """Iterate through domain subdirectories in a package."""
    try:
        base_module = importlib.import_module(domain_pkg)
    except ImportError:
        logger.warning("Domain package not found", package=domain_pkg)
        return []

    if not hasattr(base_module, "__path__"):
        logger.warning("Package has no __path__", package=domain_pkg)
        return []

    base_path = Path(base_module.__path__[0])
    results: list[tuple[str, Path]] = []

    for domain_dir in sorted(base_path.iterdir()):
        if not domain_dir.is_dir():
            continue
        if domain_dir.name.startswith(("_", ".")):
            continue

        domain_module_path = f"{domain_pkg}.{domain_dir.name}"
        results.append((domain_module_path, domain_dir))

    return results


def _discover_controllers_in_submodule(controller_module_path: str) -> list[type[Controller]]:
    """Discover controllers in a single submodule path."""
    try:
        controller_module = importlib.import_module(controller_module_path)
    except ImportError:
        return []

    all_controllers: list[type[Controller]] = []

    if hasattr(controller_module, "__path__"):
        for _, modname, ispkg in pkgutil.walk_packages(controller_module.__path__, prefix=f"{controller_module_path}."):
            if ispkg:
                continue
            try:
                mod = importlib.import_module(modname)
                controllers = find_controllers_in_module(mod)
                all_controllers.extend(controllers)
            except (ImportError, AttributeError, SyntaxError) as e:
                logger.warning("Failed to import controller module", module=modname, error=str(e))

    controllers = find_controllers_in_module(controller_module)
    all_controllers.extend(controllers)

    return all_controllers


def _discover_listeners_in_submodule(listener_module_path: str) -> list["EventListener"]:
    """Discover listeners in a single submodule path."""
    try:
        listener_module = importlib.import_module(listener_module_path)
    except ImportError:
        return []

    all_listeners: list[EventListener] = []

    if hasattr(listener_module, "__path__"):
        for _, modname, ispkg in pkgutil.walk_packages(listener_module.__path__, prefix=f"{listener_module_path}."):
            if ispkg:
                continue
            try:
                mod = importlib.import_module(modname)
                listeners = find_listeners_in_module(mod)
                all_listeners.extend(listeners)
            except (ImportError, AttributeError, SyntaxError) as e:
                logger.warning("Failed to import listener module", module=modname, error=str(e))

    listeners = find_listeners_in_module(listener_module)
    all_listeners.extend(listeners)

    return all_listeners


__all__ = (
    "DomainPlugin",
    "DomainPluginConfig",
    "clear_discovery_cache",
    "discover_domain_controllers",
    "discover_domain_listeners",
    "find_controllers_in_module",
)
