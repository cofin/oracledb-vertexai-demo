# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Verify the installed litestar-security artifact and domain controller inheritance."""

import ast
from importlib.metadata import version
from pathlib import Path
from types import ModuleType

import litestar_security
from litestar_security import accounts, providers, testing
from packaging.version import Version

__all__ = (
    "ACCOUNT_EXPORTS",
    "ALLOWED_CONTROLLER_BASES",
    "FORBIDDEN_EXPORTS",
    "MINIMUM_VERSION",
    "PROVIDER_EXPORTS",
    "ROOT_EXPORTS",
    "TESTING_EXPORTS",
    "main",
)

MINIMUM_VERSION = Version("0.6.0")

ROOT_EXPORTS = (
    "AuthenticationPolicy",
    "CredentialVerifier",
    "PublicController",
    "SecureController",
    "SecurityConfig",
    "SecurityHeadersConfig",
    "SecurityPlugin",
    "WebSocketConnectAuthorization",
    "exclude",
    "requires_all_of",
    "requires_any_of",
    "requires_assurance",
    "requires_at_least",
    "requires_authenticated",
    "requires_capability",
    "requires_one_of",
    "requires_role",
    "requires_scope",
    "requires_tenant",
    "requires_tenant_role",
)
ACCOUNT_EXPORTS = (
    "LocalAccountState",
    "OperationMessage",
    "ResolvedUserAuthSession",
    "UserAuthSession",
    "UserAuthSessionResolver",
    "VerificationOutcome",
    "VerificationStatus",
)
PROVIDER_EXPORTS = ("APIKeyState", "GoogleIAPExternalIdentity", "JWKSFetchOutcome", "JWKSFetchTarget", "JWKSSource")
TESTING_EXPORTS = (
    "BackendBarrier",
    "FakeClock",
    "OAuthRequestObservation",
    "StoreConformanceFactories",
    "assert_api_key_store_conformance",
    "assert_rate_limiter_conformance",
    "assert_security_backend_conformance",
    "assert_session_registry_conformance",
)
FORBIDDEN_EXPORTS = (
    "APIKeyRecord",
    "AssertionRecordStatus",
    "ConsumeOutcome",
    "ConsumeStatus",
    "InvalidWebAuthnResponseError",
    "JWKSCacheEntry",
    "JWKSFetchRequest",
    "JWKSFetchResponse",
    "LocalAccountRecord",
    "OAuthHTTPRequest",
    "OAuthRouteStatus",
    "PasskeyRecord",
    "RequestAuthenticator",
    "RouteStatus",
    "SessionRecord",
    "StepUpRecord",
    "WebSocketConnectTokenRecord",
    "guard_all_of",
    "guard_any_of",
    "guard_at_least",
    "guard_one_of",
    "require_all_of",
    "require_any_of",
    "require_assurance",
    "require_at_least",
    "require_authenticated",
    "require_capability",
    "require_one_of",
    "require_role",
    "require_scope",
    "require_team_role",
    "require_tenant",
    "requires_team_role",
)
ALLOWED_CONTROLLER_BASES = frozenset({
    "PublicController",
    "SecureController",
    "SkillController",
    "PromptController",
    "CoffeeSkillController",
    "CoffeePromptController",
})


def main() -> None:
    """Validate version, semantic exports, removed legacy names, and controller inheritance."""
    installed = Version(version("litestar-security"))
    if installed < MINIMUM_VERSION:
        msg = f"litestar-security {installed} is below the required {MINIMUM_VERSION}"
        raise RuntimeError(msg)

    _require_exports(litestar_security, ROOT_EXPORTS)
    _require_exports(accounts, ACCOUNT_EXPORTS)
    _require_exports(providers, PROVIDER_EXPORTS)
    _require_exports(testing, TESTING_EXPORTS)

    public_modules = (litestar_security, accounts, providers, testing)
    present = [name for name in FORBIDDEN_EXPORTS if any(hasattr(module, name) for module in public_modules)]
    if present:
        msg = f"litestar-security exposes forbidden legacy names: {', '.join(present)}"
        raise RuntimeError(msg)

    _verify_controller_inheritance()


def _require_exports(module: ModuleType, names: tuple[str, ...]) -> None:
    missing = [name for name in names if not hasattr(module, name)]
    if missing:
        msg = f"{module.__name__} is missing required exports: {', '.join(missing)}"
        raise RuntimeError(msg)


def _verify_controller_inheritance() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    domain_root = repo_root / "src" / "app" / "domain"
    violations: list[str] = []
    for path in sorted(domain_root.rglob("*.py")):
        if "controllers" not in path.parts and "mcp" not in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or not node.name.endswith("Controller"):
                continue
            base_names = {_extract_base_name(base) for base in node.bases}
            if "Controller" in base_names:
                violations.append(f"{path.relative_to(repo_root)}:{node.lineno} {node.name} inherits bare Controller")
            elif not (base_names & ALLOWED_CONTROLLER_BASES):
                violations.append(
                    f"{path.relative_to(repo_root)}:{node.lineno} {node.name} must inherit PublicController or SecureController"
                )
    if violations:
        msg = "Controller security inheritance violations:\n" + "\n".join(violations)
        raise RuntimeError(msg)


def _extract_base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


if __name__ == "__main__":
    main()
