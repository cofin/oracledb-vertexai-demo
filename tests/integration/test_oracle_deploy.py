"""Integration tests for Oracle deployment tools.

Tests cover:
- Container runtime detection and operations
- Database lifecycle management (start, stop, restart, remove)
- Wallet configuration and validation
- Connection testing across both deployment modes (managed, external)
- System health checks
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from tools.oracle.container import ContainerRuntime
    from tools.oracle.database import DatabaseConfig
    from tools.oracle.health import HealthChecker
    from tools.oracle.wallet import WalletConfigurator


pytestmark = pytest.mark.anyio


class TestContainerRuntime:
    """Test container runtime abstraction."""

    def test_runtime_detection(self) -> None:
        """Test that runtime detection works."""
        from tools.oracle.container import ContainerRuntime

        runtime = ContainerRuntime()
        assert runtime.is_available(), "At least Docker or Podman should be available for tests"
        assert runtime.get_runtime_type() is not None

    def test_runtime_commands(self) -> None:
        """Test basic runtime commands."""
        from tools.oracle.container import ContainerRuntime

        runtime = ContainerRuntime()

        # Test version command (run_command returns tuple: (return_code, stdout, stderr))
        return_code, stdout, _stderr = runtime.run_command(["--version"])
        assert return_code == 0
        assert len(stdout) > 0


class TestDatabaseLifecycle:
    """Test database lifecycle operations."""

    @pytest.fixture
    def db_config(self) -> DatabaseConfig:
        """Create test database configuration."""
        from tools.oracle.database import DatabaseConfig

        return DatabaseConfig(
            container_name="oracle23ai-test",
            image="gvenzl/oracle-free:latest",
            host_port=1522,  # Use different port to avoid conflicts
            oracle_system_password="TestPassword123!",  # noqa: S106
            app_user="testuser",
            app_user_password="testpass123",  # noqa: S106
            data_volume_name="oracle23ai-test-data",
        )

    @pytest.fixture
    def runtime(self) -> ContainerRuntime:
        """Create container runtime."""
        from tools.oracle.container import ContainerRuntime

        return ContainerRuntime()

    def test_database_config_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading database config from environment."""
        from tools.oracle.database import DatabaseConfig

        monkeypatch.setenv("ORACLE23AI_PORT", "1523")
        monkeypatch.setenv("ORACLE_SYSTEM_PASSWORD", "EnvPassword123!")
        monkeypatch.setenv("ORACLE_USER", "envuser")
        monkeypatch.setenv("ORACLE_PASSWORD", "envpass123")

        config = DatabaseConfig.from_env()

        assert config.host_port == 1523
        assert config.oracle_system_password == "EnvPassword123!"  # noqa: S105
        assert config.app_user == "envuser"
        assert config.app_user_password == "envpass123"  # noqa: S105

    @pytest.mark.slow
    def test_database_status_check(self, runtime: ContainerRuntime, db_config: DatabaseConfig) -> None:
        """Test database status check without starting container."""
        from tools.oracle.database import OracleDatabase

        db = OracleDatabase(runtime=runtime, config=db_config)

        # Check status of non-existent container
        is_running = db.is_running()
        assert isinstance(is_running, bool)


class TestWalletConfiguration:
    """Test wallet configuration and validation."""

    @pytest.fixture
    def wallet_configurator(self) -> WalletConfigurator:
        """Create wallet configurator."""
        from tools.oracle.wallet import WalletConfigurator

        return WalletConfigurator()

    def test_wallet_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test wallet search when no wallet exists."""
        from tools.oracle.wallet import WalletConfig, WalletConfigurator

        # Clear environment variables that might point to wallets
        monkeypatch.delenv("WALLET_LOCATION", raising=False)
        monkeypatch.delenv("TNS_ADMIN", raising=False)

        # Create a temp directory without any wallet
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        # Create configurator with empty default locations to avoid finding real wallet
        config = WalletConfig(default_locations=[empty_dir])
        configurator = WalletConfigurator(config=config)

        # Search in empty directory
        found = configurator.find_wallet()
        assert found is None

    def test_wallet_validation_missing_files(
        self, wallet_configurator: WalletConfigurator, tmp_path: Path
    ) -> None:
        """Test wallet validation with missing required files."""
        # Create empty wallet directory
        wallet_dir = tmp_path / "wallet"
        wallet_dir.mkdir()

        wallet_info = wallet_configurator.validate_wallet(wallet_dir)

        assert wallet_info.is_valid is False
        assert wallet_info.validation_errors is not None
        assert len(wallet_info.validation_errors) > 0
        assert any("cwallet.sso" in err for err in wallet_info.validation_errors)

    def test_wallet_validation_with_files(
        self, wallet_configurator: WalletConfigurator, tmp_path: Path
    ) -> None:
        """Test wallet validation with required files present."""
        # Create wallet directory with required files
        wallet_dir = tmp_path / "wallet"
        wallet_dir.mkdir()

        # Create minimal required files
        (wallet_dir / "cwallet.sso").write_text("")
        (wallet_dir / "sqlnet.ora").write_text("WALLET_LOCATION = (SOURCE = (METHOD = file))")

        # Create minimal tnsnames.ora
        tnsnames_content = """
db_high = (DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=example.com)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=db_high)))
db_low = (DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=example.com)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=db_low)))
"""
        (wallet_dir / "tnsnames.ora").write_text(tnsnames_content)

        wallet_info = wallet_configurator.validate_wallet(wallet_dir)

        assert wallet_info.is_valid is True
        assert wallet_info.has_cwallet is True
        assert wallet_info.has_tnsnames is True
        assert wallet_info.has_sqlnet is True
        assert wallet_info.services is not None
        assert "db_high" in wallet_info.services
        assert "db_low" in wallet_info.services

    def test_parse_tnsnames(self, wallet_configurator: WalletConfigurator, tmp_path: Path) -> None:
        """Test parsing tnsnames.ora file."""
        wallet_dir = tmp_path / "wallet"
        wallet_dir.mkdir()

        # Create tnsnames.ora with various service types
        tnsnames_content = """
# Comment line
mydb_high = (DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=host1.example.com)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=mydb_high)))
mydb_medium = (DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=host2.example.com)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=mydb_medium)))
mydb_low = (DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=host3.example.com)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=mydb_low)))
mydb_tp = (DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=host4.example.com)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=mydb_tp)))
"""
        (wallet_dir / "tnsnames.ora").write_text(tnsnames_content)

        services = wallet_configurator.parse_tnsnames(wallet_dir)

        assert len(services) >= 4
        assert "mydb_high" in services
        assert "mydb_medium" in services
        assert "mydb_low" in services
        assert "mydb_tp" in services


class TestConnectionTesting:
    """Test connection testing across deployment modes."""

    def test_deployment_mode_detection_managed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test managed mode detection."""
        from tools.oracle.connection import DeploymentMode, detect_deployment_mode

        # Clear any existing database environment variables
        for key in ["DATABASE_URL", "WALLET_PASSWORD", "DATABASE_HOST"]:
            monkeypatch.delenv(key, raising=False)

        mode = detect_deployment_mode()
        assert mode == DeploymentMode.MANAGED

    def test_deployment_mode_detection_external_with_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test external mode detection with DATABASE_HOST."""
        from tools.oracle.connection import DeploymentMode, detect_deployment_mode

        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("DATABASE_HOST", "remote.example.com")

        mode = detect_deployment_mode()
        assert mode == DeploymentMode.EXTERNAL

    def test_deployment_mode_detection_external_with_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test external mode detection with DATABASE_URL."""
        from tools.oracle.connection import DeploymentMode, detect_deployment_mode

        monkeypatch.setenv("DATABASE_URL", "oracle+oracledb://user:pass@service_high")

        mode = detect_deployment_mode()
        assert mode == DeploymentMode.EXTERNAL

    def test_connection_config_from_env_managed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading connection config for managed mode."""
        from tools.oracle.connection import ConnectionConfig, DeploymentMode

        # Clear external/wallet variables
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("WALLET_PASSWORD", raising=False)
        monkeypatch.delenv("DATABASE_HOST", raising=False)
        monkeypatch.delenv("WALLET_LOCATION", raising=False)
        monkeypatch.delenv("TNS_ADMIN", raising=False)

        # Set managed mode variables
        monkeypatch.setenv("DATABASE_USER", "manageduser")
        monkeypatch.setenv("DATABASE_PASSWORD", "managedpass")
        monkeypatch.setenv("ORACLE23AI_PORT", "1521")
        monkeypatch.setenv("DATABASE_SERVICE_NAME", "FREEPDB1")

        config = ConnectionConfig.from_env()

        assert config.mode == DeploymentMode.MANAGED
        assert config.user == "manageduser"
        assert config.password == "managedpass"  # noqa: S105


class TestHealthChecker:
    """Test system health checking."""

    @pytest.fixture
    def health_checker(self) -> HealthChecker:
        """Create health checker."""
        from tools.oracle.health import HealthChecker

        return HealthChecker()

    def test_check_runtime(self, health_checker: HealthChecker) -> None:
        """Test runtime health check."""
        component = health_checker.check_runtime()

        assert component.name == "Container Runtime"
        assert component.status is not None
        assert component.message is not None

    def test_check_sqlcl(self, health_checker: HealthChecker) -> None:
        """Test SQLcl health check."""
        component = health_checker.check_sqlcl()

        assert component.name == "SQLcl"
        assert component.status is not None
        # SQLcl might not be installed, which is OK
        # Just check that check doesn't crash

    def test_detect_deployment_mode(self, health_checker: HealthChecker) -> None:
        """Test deployment mode detection."""
        mode = health_checker.detect_deployment_mode()

        assert mode is not None
        from tools.oracle.connection import DeploymentMode
        assert isinstance(mode, DeploymentMode)

    def test_status_color_mapping(self, health_checker: HealthChecker) -> None:
        """Test status color mapping."""
        from tools.oracle.health import HealthStatus

        # Test all status colors
        assert health_checker.get_status_color(HealthStatus.HEALTHY) == "green"
        assert health_checker.get_status_color(HealthStatus.DEGRADED) == "yellow"
        assert health_checker.get_status_color(HealthStatus.UNHEALTHY) == "red"
        assert health_checker.get_status_color(HealthStatus.UNKNOWN) == "dim"
        assert health_checker.get_status_color(HealthStatus.NOT_APPLICABLE) == "dim"

    def test_status_icon_mapping(self, health_checker: HealthChecker) -> None:
        """Test status icon mapping."""
        from tools.oracle.health import HealthStatus

        # Test all status icons
        assert health_checker.get_status_icon(HealthStatus.HEALTHY) == "✓"
        assert health_checker.get_status_icon(HealthStatus.DEGRADED) == "⚠"
        assert health_checker.get_status_icon(HealthStatus.UNHEALTHY) == "✗"
        assert health_checker.get_status_icon(HealthStatus.UNKNOWN) == "?"
        assert health_checker.get_status_icon(HealthStatus.NOT_APPLICABLE) == "-"
