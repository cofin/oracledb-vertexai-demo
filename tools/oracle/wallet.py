# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Wallet configurator for Oracle Autonomous AI Database connections."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm
from sqlspec.adapters.oracledb import extract_oracle_wallet_zip, parse_tnsnames_ora

__all__ = (
    "TNSParseError",
    "WalletConfig",
    "WalletConfigurator",
    "WalletError",
    "WalletExtractionError",
    "WalletInfo",
    "WalletNotFoundError",
    "WalletValidationError",
)


class WalletError(Exception):
    """Base exception for wallet operations."""


class WalletNotFoundError(WalletError):
    """Raised when an Oracle wallet cannot be located."""


class WalletValidationError(WalletError):
    """Raised when wallet validation fails."""


class WalletExtractionError(WalletError):
    """Raised when wallet extraction fails."""


class TNSParseError(WalletError):
    """Raised when ``tnsnames.ora`` parsing fails."""


@dataclass(slots=True)
class WalletInfo:
    """Validation and service metadata for an Oracle mTLS wallet."""

    wallet_dir: Path
    zip_path: Path | None = None
    has_cwallet: bool = False
    has_ewallet: bool = False
    has_tnsnames: bool = False
    has_sqlnet: bool = False
    has_keystore: bool = False
    has_truststore: bool = False
    services: list[str] | None = None
    is_valid: bool = False
    validation_errors: list[str] | None = None

    @property
    def required_files_present(self) -> bool:
        """Return True when ``cwallet.sso``, ``tnsnames.ora``, and ``sqlnet.ora`` exist."""
        return self.has_cwallet and self.has_tnsnames and self.has_sqlnet


@dataclass(slots=True)
class WalletConfig:
    """Search locations and expected filenames for Oracle wallets."""

    default_locations: list[Path] | None = None
    required_files: list[str] | None = None
    optional_files: list[str] | None = None

    def __post_init__(self) -> None:
        """Populate default search paths and file checklists."""
        if self.default_locations is None:
            candidates = [Path(".envs/tns")]
            for env_key in ("WALLET_LOCATION", "TNS_ADMIN"):
                env_val = os.getenv(env_key, "").strip()
                if env_val:
                    candidates.append(Path(env_val))
            candidates.append(Path.home() / ".oracle" / "wallet")
            self.default_locations = candidates

        if self.required_files is None:
            self.required_files = ["cwallet.sso", "tnsnames.ora", "sqlnet.ora"]

        if self.optional_files is None:
            self.optional_files = ["ewallet.p12", "ewallet.pem", "keystore.jks", "truststore.jks", "ojdbc.properties"]


class WalletConfigurator:
    """Configure and validate Oracle Autonomous AI Database wallets."""

    def __init__(self, config: WalletConfig | None = None, console: Console | None = None) -> None:
        """Initialize the wallet configurator."""
        self.config = config or WalletConfig()
        self.console = console or Console()

    def configure(self, wallet_path: Path | None = None, *, interactive: bool = True) -> WalletInfo:
        """Locate, extract, and validate an Oracle wallet and print `.env` guidance."""
        self.console.rule("[bold blue]Oracle Autonomous Database Configuration", style="blue", align="left")
        self.console.print()
        self.console.print("[yellow]Checking for Oracle wallet...[/yellow]")

        found_wallet = wallet_path or self.find_wallet()
        if not found_wallet:
            self.console.print("[yellow]No wallet found[/yellow]")
            self.console.print("\n[dim]For Autonomous AI Database (or managed adb-free), set:[/dim]")
            self.console.print("  WALLET_LOCATION=./.envs/tns")
            self.console.print("  WALLET_PASSWORD=<wallet_password>")
            self.console.print("  DATABASE_URL=myatp_low")
            raise WalletNotFoundError("No wallet found. Please specify wallet location.")

        self.console.print(f"[green]✓ Wallet found: {found_wallet}[/green]")

        wallet_dir = found_wallet
        zip_path = None
        if found_wallet.is_file() and found_wallet.suffix == ".zip":
            zip_path = found_wallet
            wallet_dir = self.extract_wallet(zip_path)

        wallet_info = self.validate_wallet(wallet_dir)
        wallet_info.zip_path = zip_path

        if not wallet_info.is_valid:
            self.console.print("[red]✗ Wallet validation failed:[/red]")
            for error in wallet_info.validation_errors or []:
                self.console.print(f"  • {error}")
            raise WalletValidationError(f"Invalid wallet: {wallet_info.validation_errors}")

        if wallet_info.has_tnsnames:
            self.console.print("[green]✓ tnsnames.ora found[/green]")
            if wallet_info.services:
                self.list_services(wallet_dir, display=True)

        env_vars = self.get_env_config(wallet_dir)
        self.display_configuration_help(wallet_info, env_vars)

        if interactive and Confirm.ask("Set TNS_ADMIN for current session?", default=True):
            self.set_tns_admin(wallet_dir)

        return wallet_info

    def find_wallet(self, start_path: Path | None = None) -> Path | None:
        """Search ``start_path`` and default wallet locations for a wallet directory or ``.zip``."""
        if start_path and start_path.exists():
            if start_path.is_file() and start_path.suffix == ".zip":
                return start_path
            if start_path.is_dir() and (start_path / "cwallet.sso").exists():
                return start_path

        for location in self.config.default_locations or []:
            if not location.exists():
                continue
            if location.is_dir():
                if (location / "cwallet.sso").exists():
                    return location
                for zip_file in sorted(location.glob("Wallet_*.zip")):
                    return zip_file
            if location.is_file() and location.suffix == ".zip":
                return location

        return None

    def extract_wallet(
        self, zip_path: Path, dest_dir: Path | None = None, *, wallet_password: str | None = None
    ) -> Path:
        """Extract a wallet ``.zip`` archive via SQLSpec's ``extract_oracle_wallet_zip``."""
        if not zip_path.exists():
            raise WalletExtractionError(f"Wallet zip file not found: {zip_path}")

        default_target = self.config.default_locations[0] if self.config.default_locations else Path(".envs/tns")
        target_dir = dest_dir if dest_dir is not None else default_target
        target_dir.mkdir(parents=True, exist_ok=True)
        resolved_password = wallet_password if wallet_password is not None else os.getenv("WALLET_PASSWORD")
        try:
            resolved = extract_oracle_wallet_zip(zip_path, target_dir, wallet_password=resolved_password)
        except Exception as exc:
            raise WalletExtractionError(f"Failed to extract wallet: {exc}") from exc

        resolved_path = resolved.resolve()
        self.console.print(f"[green]✓ Extracted wallet to {resolved_path}[/green]")
        return resolved_path

    def validate_wallet(self, wallet_dir: Path) -> WalletInfo:
        """Validate required files and parseable service aliases in ``wallet_dir``."""
        errors: list[str] = []
        if not wallet_dir.exists():
            errors.append(f"Wallet directory not found: {wallet_dir}")
            return WalletInfo(wallet_dir=wallet_dir, is_valid=False, validation_errors=errors)

        has_cwallet = (wallet_dir / "cwallet.sso").exists()
        has_ewallet = (wallet_dir / "ewallet.p12").exists() or (wallet_dir / "ewallet.pem").exists()
        has_tnsnames = (wallet_dir / "tnsnames.ora").exists()
        has_sqlnet = (wallet_dir / "sqlnet.ora").exists()
        has_keystore = (wallet_dir / "keystore.jks").exists()
        has_truststore = (wallet_dir / "truststore.jks").exists()

        errors.extend(
            f"Missing required file: {required_file}"
            for required_file in self.config.required_files or []
            if not (wallet_dir / required_file).exists()
        )

        services: list[str] = []
        if has_tnsnames:
            try:
                services = self.parse_tnsnames(wallet_dir)
            except TNSParseError as exc:
                errors.append(f"Failed to parse tnsnames.ora: {exc}")

        return WalletInfo(
            wallet_dir=wallet_dir,
            has_cwallet=has_cwallet,
            has_ewallet=has_ewallet,
            has_tnsnames=has_tnsnames,
            has_sqlnet=has_sqlnet,
            has_keystore=has_keystore,
            has_truststore=has_truststore,
            services=services,
            is_valid=len(errors) == 0,
            validation_errors=errors or None,
        )

    def parse_tnsnames(self, wallet_dir: Path) -> list[str]:
        """Parse ``tnsnames.ora`` service aliases via SQLSpec's ``parse_tnsnames_ora``."""
        tnsnames_path = wallet_dir / "tnsnames.ora"
        if not tnsnames_path.exists():
            raise TNSParseError(f"tnsnames.ora not found in {wallet_dir}")

        try:
            parsed = parse_tnsnames_ora(tnsnames_path)
        except Exception as exc:
            raise TNSParseError(f"Failed to parse tnsnames.ora: {exc}") from exc
        return list(parsed)

    def list_services(self, wallet_dir: Path, *, display: bool = True) -> list[str]:
        """List available database services in ``tnsnames.ora``."""
        services = self.parse_tnsnames(wallet_dir)
        if display and services:
            self.console.print("\n[bold]Available database services:[/bold]")
            for idx, service in enumerate(services, 1):
                lower = service.lower()
                if lower.endswith("_high"):
                    priority = "[green]High[/green]"
                elif lower.endswith("_medium"):
                    priority = "[yellow]Medium[/yellow]"
                elif lower.endswith("_low"):
                    priority = "[blue]Low[/blue]"
                elif lower.endswith("_tp"):
                    priority = "[cyan]TP (Transaction Processing)[/cyan]"
                elif lower.endswith("_tpurgent"):
                    priority = "[red]TP Urgent[/red]"
                else:
                    priority = "Standard"
                self.console.print(f"  {idx}. [bold]{service}[/bold] - {priority}")
        return services

    def get_env_config(self, wallet_dir: Path, service_name: str | None = None) -> dict[str, str]:
        """Return `.env` keys pointing at ``wallet_dir``."""
        resolved = str(wallet_dir.resolve())
        env_vars = {"WALLET_LOCATION": resolved, "TNS_ADMIN": resolved}
        if service_name:
            env_vars["DATABASE_URL"] = service_name
        return env_vars

    def set_tns_admin(self, wallet_dir: Path) -> None:
        """Export ``TNS_ADMIN`` and ``WALLET_LOCATION`` into the current process environment."""
        wallet_path = str(wallet_dir.resolve())
        os.environ["TNS_ADMIN"] = wallet_path
        os.environ["WALLET_LOCATION"] = wallet_path
        self.console.print(f"[green]✓ Set TNS_ADMIN={wallet_path}[/green]")

    def display_configuration_help(self, wallet_info: WalletInfo, env_vars: dict[str, str]) -> None:
        """Render `.env` configuration instructions for ``DatabaseSettings``."""
        self.console.print()
        self.console.print("[dim]Configure these in your .env file:[/dim]")
        for key, value in env_vars.items():
            self.console.print(f"  {key}={value}")
        if wallet_info.services:
            self.console.print(f"  DATABASE_URL={wallet_info.services[0]}")
        self.console.print("  WALLET_PASSWORD=<your_wallet_password>")
        self.console.print("  DATABASE_USER=<your_username>")
        self.console.print("  DATABASE_PASSWORD=<your_password>")
        self.console.print()
