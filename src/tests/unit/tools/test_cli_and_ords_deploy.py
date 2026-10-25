# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for packaged ORDS CDN SQL, Cloud Run build alignment, and tools CLI utilities."""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import oracledb
import pytest
from click.testing import CliRunner
from rich.console import Console
from tools.cli.doctor import doctor_command
from tools.cli.install import install_sqlcl_with_config
from tools.lib.utils import create_env_interactive, detect_deployment_mode, write_antigravity_mcp_config
from tools.oracle.sqlcl_installer import SQLclConfig, SQLclInstaller

from app.cli._helpers.ords import configure_apex_cdn_helper, parse_plsql_block
from app.lib.settings import BASE_DIR, Settings
from app.utils.serialization import decode_json, format_json

if TYPE_CHECKING:
    from pytest import MonkeyPatch

REPO_ROOT = BASE_DIR.parents[1]
DEPLOY_SQL_DIR = BASE_DIR / "db" / "sql" / "deploy"
LOW_CPU_COUNT = "2"
LOW_MEM_BYTES = str(4 * 1024**3)


def _build_mock_connection(output_lines: list[str] | None = None) -> MagicMock:
    """Create a mocked python-oracledb connection with DBMS_OUTPUT cursor variables."""
    emitted = output_lines if output_lines is not None else ["APEX IMAGE_PREFIX successfully updated to CDN"]
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_cursor.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_cursor

    mock_num_lines_var = MagicMock()
    mock_num_lines_var.getvalue.side_effect = [len(emitted), 0]
    mock_cursor.var.return_value = mock_num_lines_var

    mock_lines_var = MagicMock()
    mock_lines_var.getvalue.side_effect = [emitted, []]
    mock_cursor.arrayvar.return_value = mock_lines_var
    return mock_conn


def _parse_dotenv_lines(content: str) -> dict[str, str]:
    """Parse non-comment `KEY=VALUE` lines from a generated `.env` file."""
    entries: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        entries[key.strip()] = value.strip()
    return entries


class _StubNotInPathInstaller(SQLclInstaller):
    """Test double simulating SQLcl installed outside the active shell PATH."""

    def install(self, *, force: bool = False, verify_path: bool = True) -> Path:
        """Return the configured install directory without network I/O."""
        del force, verify_path
        return self.config.install_dir

    def is_in_path(self) -> bool:
        """Simulate an install directory absent from PATH."""
        return False

    def get_path_instructions(self) -> str:
        """Return multi-line shell PATH setup instructions."""
        return f'  export PATH="$PATH:{self.config.install_dir}"\n  hash -r'


def test_packaged_deploy_sql_files_exist_and_parse_cleanly(tmp_path: Path) -> None:
    """Verify `configure-apex-cdn.sql` and `revert-apex-cdn.sql` live under `BASE_DIR/db/sql/deploy`."""
    configure_sql = DEPLOY_SQL_DIR / "configure-apex-cdn.sql"
    revert_sql = DEPLOY_SQL_DIR / "revert-apex-cdn.sql"

    assert configure_sql.is_file()
    assert revert_sql.is_file()

    for sql_file in (configure_sql, revert_sql):
        parsed = parse_plsql_block(sql_file)
        assert "DECLARE" in parsed
        assert "apex_instance_admin.set_parameter" in parsed
        assert "END;" in parsed
        for line in parsed.splitlines():
            stripped = line.strip()
            assert not stripped.upper().startswith("SET ")
            assert stripped != "/"

    with pytest.raises(FileNotFoundError):
        parse_plsql_block(tmp_path / "missing.sql")


def test_configure_apex_cdn_helper_resolves_packaged_sql_for_sysdba(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Verify `configure_apex_cdn_helper` loads packaged SQL via `Settings.from_env()` on standard PDBs."""
    monkeypatch.chdir(tmp_path)
    for key in (
        "DATABASE_URL",
        "DATABASE_DSN",
        "WALLET_LOCATION",
        "WALLET_PASSWORD",
        "TNS_ADMIN",
        "DATABASE_ADMIN_PASSWORD",
        "ORACLE_ADMIN_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DATABASE_HOST", "10.10.0.10")
    monkeypatch.setenv("DATABASE_PORT", "1521")
    monkeypatch.setenv("DATABASE_SERVICE_NAME", "freepdb1")
    Settings.from_env.cache_clear()

    mock_conn = _build_mock_connection()
    mock_connect = MagicMock(return_value=mock_conn)
    monkeypatch.setattr("app.cli._helpers.ords.oracledb.connect", mock_connect)

    configure_apex_cdn_helper("sysdba-secret")

    mock_connect.assert_called_once_with(
        user="SYS", password="sysdba-secret", dsn="10.10.0.10:1521/freepdb1", mode=oracledb.AUTH_MODE_SYSDBA
    )
    executed_sql = mock_conn.cursor.return_value.execute.call_args[0][0]
    assert "https://static.oracle.com/cdn/apex/26.1.0/" in executed_sql


def test_configure_apex_cdn_helper_supports_autonomous_admin_wallet(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Verify `configure_apex_cdn_helper` connects as `ADMIN` with wallet when `settings.db.is_autonomous`."""
    monkeypatch.chdir(tmp_path)
    wallet_dir = tmp_path / "wallet"
    wallet_dir.mkdir()
    (wallet_dir / "tnsnames.ora").write_text("myatp_low = (DESCRIPTION=...)\n", encoding="utf-8")

    monkeypatch.delenv("DATABASE_SYSTEM_PASSWORD", raising=False)
    monkeypatch.delenv("ORACLE_SYSTEM_PASSWORD", raising=False)
    monkeypatch.setenv("DATABASE_URL", "myatp_low")
    monkeypatch.setenv("WALLET_LOCATION", str(wallet_dir))
    monkeypatch.setenv("WALLET_PASSWORD", "WalletSecret1")
    monkeypatch.setenv("DATABASE_ADMIN_PASSWORD", "AdminSecret1")
    Settings.from_env.cache_clear()

    mock_extract = MagicMock(return_value=wallet_dir)
    monkeypatch.setattr("app.cli._helpers.ords.extract_oracle_wallet_zip", mock_extract)
    mock_conn = _build_mock_connection()
    mock_connect = MagicMock(return_value=mock_conn)
    monkeypatch.setattr("app.cli._helpers.ords.oracledb.connect", mock_connect)

    configure_apex_cdn_helper()

    mock_extract.assert_called_once_with(wallet_dir, wallet_password="WalletSecret1")
    mock_connect.assert_called_once_with(
        user="ADMIN",
        password="AdminSecret1",
        dsn="myatp_low",
        config_dir=str(wallet_dir),
        wallet_location=str(wallet_dir),
        wallet_password="WalletSecret1",
    )


def test_install_sqlcl_with_config_prints_path_instructions_by_line(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Verify `install_sqlcl_with_config` prints PATH setup lines whole rather than character-by-character."""
    buffer = io.StringIO()
    capture_console = Console(file=buffer, force_terminal=False, color_system=None, width=120)
    monkeypatch.setattr("tools.cli.install.console", capture_console)

    config = SQLclConfig(install_dir=tmp_path / "bin")
    install_sqlcl_with_config(config, _StubNotInPathInstaller, force=False)

    rendered_lines = [line.strip() for line in buffer.getvalue().splitlines() if line.strip()]
    assert f'export PATH="$PATH:{config.install_dir}"' in rendered_lines
    assert "hash -r" in rendered_lines
    single_char_lines = [line for line in rendered_lines if len(line) == 1]
    assert single_char_lines == []


def test_create_env_interactive_managed_writes_adb_free_defaults(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Verify `create_env_interactive` writes managed `adb-free` wallet defaults and `LITESTAR_PORT=8000`."""
    monkeypatch.chdir(tmp_path)

    created = create_env_interactive("managed", non_interactive=True)

    assert created is True
    env_file = tmp_path / ".env"
    assert env_file.is_file()
    entries = _parse_dotenv_lines(env_file.read_text(encoding="utf-8"))
    assert entries["DATABASE_DEPLOYMENT_MODE"] == "managed"
    assert entries["DATABASE_USER"] == "app"
    assert entries["DATABASE_PASSWORD"] == "SuperSecret1"
    assert entries["DATABASE_URL"] == "myatp_low"
    assert entries["WALLET_LOCATION"] == "./.envs/tns"
    assert entries["WALLET_PASSWORD"] == "SuperSecret1"
    assert entries["LITESTAR_PORT"] == "8000"


def test_detect_deployment_mode_honors_explicit_env_override(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Verify `detect_deployment_mode` honors `DATABASE_DEPLOYMENT_MODE=managed` even when `DATABASE_URL` is set."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "myatp_low")
    monkeypatch.setenv("DATABASE_DEPLOYMENT_MODE", "managed")
    assert detect_deployment_mode() == "managed"

    monkeypatch.setenv("DATABASE_DEPLOYMENT_MODE", "external")
    assert detect_deployment_mode() == "external"

    monkeypatch.delenv("DATABASE_DEPLOYMENT_MODE", raising=False)
    assert detect_deployment_mode() == "external"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_HOST", raising=False)
    assert detect_deployment_mode() == "managed"


def test_write_antigravity_mcp_config_preserves_existing_servers(tmp_path: Path) -> None:
    """Verify `write_antigravity_mcp_config` merges servers cleanly via `app.utils.serialization`."""
    existing_path = tmp_path / ".agents" / "mcp_config.json"
    existing_path.parent.mkdir(parents=True)
    existing_path.write_text(
        format_json({"mcpServers": {"custom-server": {"command": "echo", "args": ["ok"]}}}), encoding="utf-8"
    )

    written_path = write_antigravity_mcp_config("workspace", workspace_root=tmp_path)

    assert written_path == existing_path
    merged = decode_json(written_path.read_text(encoding="utf-8"))
    assert "custom-server" in merged["mcpServers"]
    assert merged["mcpServers"]["sqlcl"] == {"command": "sql", "args": ["-mcp"]}
    assert merged["mcpServers"]["oracle-toolbox"]["command"] == "toolbox"


def test_doctor_managed_checks_adb_free_resources_and_wallet_readiness(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Verify `doctor` inspects CPU/memory thresholds, `cymbal-adb-free`, and `.envs/tns/tnsnames.ora`."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DATABASE_DEPLOYMENT_MODE=managed\n", encoding="utf-8")
    tns_dir = tmp_path / ".envs" / "tns"
    tns_dir.mkdir(parents=True)
    (tns_dir / "tnsnames.ora").write_text("myatp_low = (DESCRIPTION=...)\n", encoding="utf-8")
    monkeypatch.delenv("WALLET_LOCATION", raising=False)
    monkeypatch.delenv("TNS_ADMIN", raising=False)

    def fake_which(binary: str) -> str | None:
        if binary in {"uv", "docker"}:
            return f"/usr/bin/{binary}"
        return None

    def fake_run_command(cmd: list[str], check: bool = True) -> tuple[int, str, str]:
        del check
        joined = " ".join(cmd)
        if cmd[:2] == ["uv", "--version"]:
            return 0, "uv 0.9.0\n", ""
        if "{{.NCPU}}" in joined:
            return 0, f"{LOW_CPU_COUNT}\n", ""
        if "{{.MemTotal}}" in joined:
            return 0, f"{LOW_MEM_BYTES}\n", ""
        if "inspect" in cmd and "cymbal-adb-free" in joined:
            return 0, "true\n", ""
        return 1, "", ""

    monkeypatch.setattr("tools.cli.doctor.shutil.which", fake_which)
    monkeypatch.setattr("tools.cli.doctor.run_command", fake_run_command)

    human_result = CliRunner().invoke(doctor_command, ["--mode", "managed"])
    assert human_result.exit_code == 0, human_result.output
    assert "4" in human_result.output
    assert "8 GiB" in human_result.output
    assert "cymbal-adb-free" in human_result.output
    assert "tnsnames.ora" in human_result.output

    json_result = CliRunner().invoke(doctor_command, ["--mode", "managed", "--json"])
    assert json_result.exit_code == 0, json_result.output
    payload = decode_json(json_result.output)
    assert payload["overall"] is True
    adb_info = payload["adb_free"]
    assert adb_info["cpus"] == int(LOW_CPU_COUNT)
    assert adb_info["cpu_ok"] is False
    assert adb_info["memory_ok"] is False
    assert adb_info["container_name"] == "cymbal-adb-free"
    assert adb_info["container_running"] is True
    assert adb_info["wallet_ready"] is True
    assert adb_info["wallet_tnsnames"].endswith("tnsnames.ora")


def test_dockerfile_and_cloudbuild_align_onefile_and_ords_deploy() -> None:
    """Verify `Dockerfile` defaults `TARGETARCH=amd64` and `cloudbuild.yaml` builds the PyApp onefile first."""
    dockerfile_text = (REPO_ROOT / "tools" / "deploy" / "docker" / "Dockerfile").read_text(encoding="utf-8")
    cloudbuild_text = (REPO_ROOT / "tools" / "deploy" / "gcp" / "cloudbuild.yaml").read_text(encoding="utf-8")

    assert "ARG TARGETARCH=amd64" in dockerfile_text
    assert "dist/coffee-amd64-linux-gnu" in cloudbuild_text
    assert cloudbuild_text.index("dist/coffee-amd64-linux-gnu") < cloudbuild_text.index("--file")
    assert "tools/deploy/gcp/configure-apex-cdn.sql" not in cloudbuild_text
    assert "26.3" in cloudbuild_text
