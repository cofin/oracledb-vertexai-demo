# Research: Oracle APEX 26.1 & APEXlang Integration

## Executive Summary
* **Latest APEX Release**: Oracle APEX 26.1 (released May 14, 2026) is the absolute latest version.
* **Key Feature (APEXlang)**: APEXlang is a new open, declarative application specification language that represents applications as small, human-readable, and diffable `.apx` files. It is explicitly optimized for AI understanding, version control, and CI/CD pipelines.
* **Stack Integration Options**:
  * **Option A (Custom Scripting on `gvenzl/oracle-free`)**: Requires manual downloading of APEX (due to Oracle SSO authentication), custom startup scripting, and running an ORDS container as a sidecar.
  * **Option B (Autonomous DB Free Container - Recommended)**: Switch the stack's base container to `container-registry.oracle.com/database/adb-free:latest-26ai`, which has APEX 26.1, ORDS, and Database Actions pre-installed and pre-configured.
* **Autonomous Container Alterations**: Using the Autonomous Container requires mapping HTTPS port `8443`, configuring `ADMIN_PASSWORD`/`WALLET_PASSWORD`, using the `my_atp_low` service name, and managing TLS connection verification (e.g., using `ssl_context` in python-oracledb Thin mode).

---

## 1. APEX 26.1 & APEXlang

### APEXlang Details
APEXlang is designed to resolve enterprise friction with low-code application lifecycle management:
* **Structured Format**: Applications are no longer exported as massive, opaque SQL files. Instead, they are represented as directories of `.apx` files containing clear YAML-like declarative blocks for each component (pages, regions, buttons, shared components).
* **AI-Optimized**: Large Language Models (LLMs) can read and generate `.apx` representations easily. AI agents can suggest DDL modifications or app features directly in the workspace codebase.
* **CI/CD & Source Control**: Clean diffs allow standard git workflows, PR reviews, and linting.

---

## 2. Integration Options

### Option A: Installing on `gvenzl/oracle-free:latest`

This approach keeps our current database container image but installs APEX 26.1 into it at runtime.

#### Setup Workflow
1. **Manual Downloader Action**:
   Because Oracle downloads require SSO authentication, the developer must download `apex_26.1_en.zip` and place it in `tools/oracle/downloads/` on the host.
2. **Mount Setup**:
   Map the download folder and a setup script to the container's entrypoint:
   * Local folder: `tools/oracle/downloads/` -> Container: `/opt/oracle/downloads/`
   * Script: `tools/oracle/on_init/10_install_apex.sh` -> Container: `/container-entrypoint-initdb.d/10_install_apex.sh`
3. **Initialization Script (`10_install_apex.sh`)**:
   ```bash
   #!/bin/bash
   set -e

   if [ -f "/opt/oracle/downloads/apex_26.1_en.zip" ]; then
       echo "Extracting Oracle APEX 26.1..."
       unzip -q /opt/oracle/downloads/apex_26.1_en.zip -d /opt/oracle/
       cd /opt/oracle/apex

       echo "Installing APEX in FREEPDB1..."
       sqlplus sys/${ORACLE_PASSWORD}@FREEPDB1 as sysdba @apexins.sql SYSAUX SYSAUX TEMP /i/

       echo "Configuring APEX REST Services..."
       # Pass passwords for APEX listener/REST public users
       sqlplus sys/${ORACLE_PASSWORD}@FREEPDB1 as sysdba @apex_rest_config.sql ${APP_USER_PASSWORD} ${APP_USER_PASSWORD}

       echo "Setting APEX Admin password..."
       # Non-interactive password change
       sqlplus sys/${ORACLE_PASSWORD}@FREEPDB1 as sysdba @apxchpwd.sql ${APP_USER_PASSWORD}
   else
       echo "WARNING: apex_26.1_en.zip not found in /opt/oracle/downloads/. Skipping APEX installation."
   fi
   ```
4. **ORDS Sidecar**:
   Add a second container running `container-registry.oracle.com/database/ords:latest` connected to the `oraclefree` container. It requires configuration files mapped to serve APEX images (`/opt/oracle/apex/images` mapped as `/i/`).

---

### Option B: Transitioning to the Official Oracle Autonomous Container (Recommended)

Instead of manual installation, we run the official Oracle Autonomous Database Free Container (`adb-free:latest-26ai`), which comes with APEX 26.1 and ORDS pre-installed.

#### Setup Workflow
1. **Container Start**:
   Update `tools/oracle/database.py` (specifically `_build_run_command`) to run the Autonomous container:
   ```python
   cmd = [
       "run", "-d",
       "--name", "oracle-adb-free",
       "-p", "1521:1521",    # TLS (walletless) connection port
       "-p", "8443:8443",    # HTTPS port (APEX and Database Actions)
       "-e", f"ADMIN_PASSWORD={self.config.oracle_system_password}",
       "-e", f"WALLET_PASSWORD={self.config.oracle_system_password}",
       "--cap-add", "SYS_ADMIN",
       "--device", "/dev/fuse",
       "-v", f"{self.config.data_volume_name}:/data",
       "container-registry.oracle.com/database/adb-free:latest-26ai"
   ]
   ```
2. **Accessing APEX**:
   APEX will be instantly available on the host at `https://localhost:8443/ords/apex` using the `ADMIN` username and password.

---

## 3. Required Stack Alterations for Autonomous Database (Option B)

### DSN & Service Name Configurations
The Autonomous DB Container initializes database services named `my_atp` (Autonomous Transaction Processing).
* **Service Name**: Replace `FREEPDB1` with `my_atp_low` (or `my_atp_medium` / `my_atp_high` depending on performance requirements).
* **Host Port**: Uses port `1521` for TLS connections (no wallet files required) or `1522` for mTLS (which requires downloading the wallet zip from the container).

### TLS & Verification Bypass for Development
Autonomous Database enforces SSL (TCPS) connections. Because the container uses a self-signed certificate, python-oracledb Thin mode will fail TLS verification by default.
* **Alteration**: Modify `create_config` in [settings.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/src/app/lib/settings.py) to configure `ssl_context` with verification disabled for local development:
  ```python
  import ssl

  # Build ssl_context to bypass validation for local self-signed certs
  ctx = ssl.create_default_context()
  ctx.check_hostname = False
  ctx.verify_mode = ssl.CERT_NONE

  pool_config = {
      "user": conn_params["user"],
      "password": conn_params["password"],
      "dsn": conn_params["dsn"],
      "min": self.POOL_MIN_SIZE,
      "max": self.POOL_MAX_SIZE,
      "ssl_context": ctx,  # Inject SSL Context
  }
  ```

---

## 4. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **SSO Authentication Wall (Option A)** | High | High | Option B avoids the SSO authentication barrier entirely because APEX is pre-installed in the container. |
| **High Resource Consumption (Option B)** | High | Medium | Autonomous DB Container requires 4 CPUs & 8 GiB RAM. Development machines must be configured to support these resource constraints. |
| **Lack of Startup Script Directory (Option B)** | High | Low | Autonomous Database Free container does not run mounted SQL/bash scripts in an `/entrypoint` directory. We must execute migration DDLs (via `sqlcl` or python-oracledb) externally from the host after the container becomes healthy. |

---

## 5. Recommended Approach

We recommend **Option B: Transitioning to the Official Oracle Autonomous Container**.

### Rationale
1. **No SSO Auth Wall**: Installing APEX manually requires developers to log in to Oracle.com, click agree, get a timed SSO token, and manually stage the ZIP file on their machine. Using `adb-free` eliminates this step completely.
2. **Simplified Stack**: We avoid running and orchestrating a separate ORDS container sidecar.
3. **Parity with OCI**: Provides 100% parity with cloud Autonomous Database environments.

---

## 6. Open Questions
1. Should we support local non-TLS connections fallback? (Autonomous Container enforces TLS, so all developers will run with SSL enabled).
2. Do we have machines with less than 8 GiB RAM allotted to Docker/Podman that would fail to run the Autonomous DB Container?
