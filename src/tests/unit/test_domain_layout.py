# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Domain layout normalization tests for Ch 2.5.

Verifies each domain (`chat`, `products`, `system`) ships ``controllers``
as a *package* (not a flat module), exports the canonical
``controllers: list[type[Controller]]`` contract, and re-exports the
expected controller classes via ``__all__``.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from litestar import Controller

DOMAIN_PACKAGES: tuple[tuple[str, frozenset[str]], ...] = (
    ("app.domain.chat.controllers", frozenset({"CoffeeChatController"})),
    (
        "app.domain.products.controllers",
        frozenset({"ProductController", "StoreController", "VectorController"}),
    ),
    (
        "app.domain.system.controllers",
        frozenset({"ExemplarController", "MetricsController", "SystemController"}),
    ),
)


@pytest.mark.parametrize(("module_path", "expected_classes"), DOMAIN_PACKAGES)
def test_controllers_module_is_package(module_path: str, expected_classes: frozenset[str]) -> None:
    """Each domain's ``controllers`` must be importable as a package, not a flat module."""
    del expected_classes
    module = importlib.import_module(module_path)
    assert hasattr(module, "__path__"), (
        f"{module_path} must be a package (have __path__); flat controllers.py files are removed in Ch 2.5"
    )


@pytest.mark.parametrize(("module_path", "expected_classes"), DOMAIN_PACKAGES)
def test_controllers_package_exports_class_list(module_path: str, expected_classes: frozenset[str]) -> None:
    """Each ``controllers/__init__.py`` must expose a ``controllers: list[type[Controller]]`` contract."""
    module = importlib.import_module(module_path)
    controllers = getattr(module, "controllers", None)
    assert controllers is not None, (
        f"{module_path} must export `controllers: list[type[Controller]]` — explicit contract for ApplicationCore"
    )
    assert isinstance(controllers, list), f"{module_path}.controllers must be a list, got {type(controllers).__name__}"
    assert all(isinstance(c, type) and issubclass(c, Controller) for c in controllers), (
        f"{module_path}.controllers entries must be Controller subclasses"
    )
    exposed = {c.__name__ for c in controllers}
    assert exposed == expected_classes, (
        f"{module_path}.controllers expected {sorted(expected_classes)}, got {sorted(exposed)}"
    )


@pytest.mark.parametrize(("module_path", "expected_classes"), DOMAIN_PACKAGES)
def test_controllers_package_reexports_classes(module_path: str, expected_classes: frozenset[str]) -> None:
    """Each controller class must be re-exported at the package root and listed in ``__all__``."""
    module = importlib.import_module(module_path)
    declared = set(getattr(module, "__all__", ()))
    missing = expected_classes - declared
    assert not missing, f"{module_path}.__all__ missing {sorted(missing)}; got {sorted(declared)}"

    for cls_name in expected_classes:
        cls = getattr(module, cls_name, None)
        assert cls is not None, f"{module_path}.{cls_name} not re-exported"
        assert issubclass(cls, Controller), f"{module_path}.{cls_name} must be a Controller subclass"


@pytest.mark.parametrize("module_path", [pkg for pkg, _ in DOMAIN_PACKAGES])
def test_legacy_flat_controllers_module_removed(module_path: str) -> None:
    """The flat ``domain/X/controllers.py`` file MUST be deleted in favor of the package layout."""
    module = importlib.import_module(module_path)
    package_init = Path(module.__file__) if module.__file__ else None
    assert package_init is not None, f"{module_path} has no __file__"
    assert package_init.name == "__init__.py", (
        f"{module_path} resolves to {package_init} — expected controllers/__init__.py (the flat file must be removed)"
    )

    domain_dir = package_init.parent.parent
    flat_file = domain_dir / "controllers.py"
    assert not flat_file.exists(), (
        f"Stale flat module remains at {flat_file}; delete after migrating contents into controllers/"
    )


def test_application_core_discovers_all_expected_controllers() -> None:
    """``ApplicationCore``'s discovery must register every controller from every domain on the app."""
    from app.utils.domains import clear_discovery_cache, discover_domain_controllers

    clear_discovery_cache()
    discovered = {c.__name__ for c in discover_domain_controllers(["app.domain"])}

    expected: set[str] = set()
    for _, classes in DOMAIN_PACKAGES:
        expected.update(classes)

    missing = expected - discovered
    assert not missing, f"DomainPlugin discovery missing controllers: {sorted(missing)}"
