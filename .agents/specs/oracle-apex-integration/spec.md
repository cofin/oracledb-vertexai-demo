# Flow Spec: oracle-apex-integration (Autonomous Container & APEX Integration with Direct Wallet Mounting)

## 1.0 Context
This spec defines the detailed implementation plan to migrate our local development database infrastructure to the official Oracle Autonomous Database Free Container (supporting APEX 26.1 and ORDS) as defined in the [Master PRD](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/.agents/specs/oracle-apex-integration/prd.md). It ensures local development uses mutual TLS (mTLS) with a direct volume bind-mount to capture the generated wallet.

---

## 2.0 Requirements
* Swap the container image to `container-registry.oracle.com/database/adb-free:latest-26ai`.
* Expose port `1521` (TLS), `1522` (mTLS), and `8443` (APEX/ORDS HTTPS).
* Configure direct bind-mount mapping host workspace `.envs/tns` to container `/u01/app/oracle/wallets/tls_wallet:z`.
* Implement automated post-startup developer schema initialization (`app` user creation and developer privileges assignment) by connecting to `myatp_low` using the newly written wallet.
* Warn developers if their Docker/Podman host memory resources are allocated below 8 GiB.

---

## 3.0 Proposed Changes

### Component: Infrastructure Automation (`tools/oracle/`)

#### [MODIFY] [database.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/tools/oracle/database.py)
* **`DatabaseConfig`**:
  * Set `image = "container-registry.oracle.com/database/adb-free:latest-26ai"`.
  * Set default `host_port = 1521` (which maps to 1522 TLS on ADB).
  * Add `host_mtls_port = 1522` and `container_mtls_port = 1522`.
  * Add `host_https_port = 8443` and `container_https_port = 8443`.
  * Add `host_mongo_port = 27017` and `container_mongo_port = 27017`.
  * Add configuration for `admin_username = "admin"` and `admin_password = "SuperSecret1"`.
  * Add `wallet_password = "SuperSecret1"`.
  * Add `app_username`/`app_password` from `DATABASE_USER`/`DATABASE_PASSWORD` for the application schema.
  * Add `wallet_location = ".envs/tns"`.
* **`_build_run_command()`**:
  * Resolve absolute path of `.envs/tns` on the host, create it if it doesn't exist, and make sure it has full write permissions (`chmod 0o777`).
  * Add port mappings:
    - `-p 1521:1522` (TLS)
    - `-p 1522:1522` (mTLS)
    - `-p 8443:8443` (HTTPS)
    - `-p 27017:27017` (MongoDB API)
  * Map environment variables: `ADMIN_PASSWORD` and `WALLET_PASSWORD` (set to `admin_password` and `wallet_password` respectively).
  * Remove environment variables `APP_USER` and `APP_USER_PASSWORD` (ADB container does not automatically initialize these).
  * Update volume mappings:
    - `-v {data_location}:/u01/data:z`
    - `-v {oradata_location}:/u01/app/oracle/oradata:z`
    - `-v {absolute_wallet_path}:/u01/app/oracle/wallets/tls_wallet:z`
  * Add container privileges flags: `--cap-add SYS_ADMIN` and `--device /dev/fuse`.
  * Remove the directory loop mounting `/container-entrypoint-initdb.d` and `/container-entrypoint-startdb.d`.
* **`initialize_db_users()`** (New Method):
  * Set `os.environ["TNS_ADMIN"] = str(absolute_wallet_path)`.
  * Connect to the local DB as `ADMIN` using the local wallet on the `myatp_low` service:
    ```python
    import oracledb
    # thin-mode wallet connection
    conn = oracledb.connect(
        user="ADMIN",
        password=self.config.admin_password,
        dsn="myatp_low",
        wallet_location=str(absolute_wallet_path),
        config_dir=str(absolute_wallet_path),
        wallet_password=self.config.wallet_password,
    )
    ```
  * Run the DDL statements to create the `app` user and grant developer privileges:
    ```sql
    DECLARE
        user_exists NUMBER;
    BEGIN
        SELECT COUNT(*) INTO user_exists FROM dba_users WHERE username = 'APP';
        IF user_exists = 0 THEN
            EXECUTE IMMEDIATE 'CREATE USER app IDENTIFIED BY "SuperSecret1"';
        ELSE
            EXECUTE IMMEDIATE 'ALTER USER app IDENTIFIED BY "SuperSecret1" ACCOUNT UNLOCK';
        END IF;
        EXECUTE IMMEDIATE 'GRANT CONNECT, RESOURCE, DB_DEVELOPER_ROLE TO app';
        EXECUTE IMMEDIATE 'GRANT UNLIMITED TABLESPACE TO app';
    END;
    ```
* **`start()`**:
  * Execute `self.initialize_db_users()` immediately after `self.wait_for_healthy(timeout=300)` succeeds.

---

### Component: Setup Utilities (`tools/lib/`)

#### [MODIFY] [utils.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/tools/lib/utils.py)
* **`create_env_interactive()`**:
  * Modify `managed` mode environment variables:
    ```env
    DATABASE_URL=oracle+oracledb://app:SuperSecret1@myatp_low
    DATABASE_USER=app
    DATABASE_PASSWORD=SuperSecret1
    WALLET_PASSWORD=SuperSecret1
    TNS_ADMIN=.envs/tns
    DATABASE_SERVICE_NAME=myatp_low
    ```

---

### Component: DevOps CLI Verification (`tools/cli/`)

#### [MODIFY] [doctor.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/tools/cli/doctor.py)
* **`doctor_command`**:
  * If the detected mode is `managed`, run a command-line check to retrieve Docker/Podman total host memory allocation.
  * For Docker: `docker info --format '{{.MemTotal}}'`
  * For Podman: `podman info --format '{{.Host.MemTotal}}'`
  * Parse the total bytes and display a warning if the memory is less than 8,500,000,000 bytes (8.5 GB).

---

### Component: App Settings (`src/app/lib/`)

#### [MODIFY] [settings.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/src/app/lib/settings.py)
* **`DatabaseSettings`**:
  * Default `SERVICE_NAME` to `"myatp_low"` instead of `"FREEPDB1"`.
* **`create_config()`**:
  * Resolve `self.WALLET_LOCATION` to an absolute path:
    ```python
    absolute_wallet_path = str(Path(self.WALLET_LOCATION).resolve())
    os.environ["TNS_ADMIN"] = absolute_wallet_path
    pool_config["wallet_location"] = absolute_wallet_path
    pool_config["config_dir"] = absolute_wallet_path
    ```
  * Keep the existing `is_autonomous` pool flow, but set both `wallet_location` and `config_dir` for thin-mode wallet connections.

---

## 4.0 Implementation Plan

### Phase 1: Environment and Settings Setup
* [x] **Task 1.1**: Update `tools/lib/utils.py` to write Autonomous-compatible variables (`DATABASE_URL`, `DATABASE_USER`, `DATABASE_PASSWORD`, `WALLET_PASSWORD`, `TNS_ADMIN`) for `managed` mode.
* [x] **Task 1.2**: Update `src/app/lib/settings.py` to force-resolve `WALLET_LOCATION` to an absolute path.
* [x] **Task 1.3**: Validate settings parsing under multi-directory execution environments by running the unit tests:
  ```bash
  uv run pytest src/tests/unit/app/lib/test_settings.py
  ```

### Phase 2: Database Container Lifecycle & Mounting
* [x] **Task 2.1**: Update `tools/oracle/database.py` with port mappings (1521, 1522, 8443, 27017), capabilities, volume targets, and system passwords.
* [x] **Task 2.2**: Add the direct directory bind mount `.envs/tns` -> `/u01/app/oracle/wallets/tls_wallet:z` within `_build_run_command()`, including absolute path resolution and permissions check.
* [x] **Task 2.3**: Implement `initialize_db_users()` to run user creation statements against `myatp_low` using the local wallet files written directly to disk.
* [x] **Task 2.4**: Update `tools/cli/doctor.py` to check for container memory requirements (8 GiB).

### Phase 3: Runtime Verification
* [x] **Task 3.1**: Run the ADB container verification path: `make start-infra`, wallet/app schema verification, migrations/fixtures, `make test`, `make stop-infra`, and idempotent `make wipe-infra`.

---

## 5.0 Verification Plan

### Automated Tests
1. **Settings Unit Verification**:
   * Run settings tests:
     ```bash
     uv run pytest src/tests/unit/app/lib/test_settings.py
     ```
2. **Database Container Spin-Up**:
   * Start the database:
     ```bash
     make start-infra
     ```
   * Confirm the container starts successfully, the wallet files are automatically generated in `.envs/tns`, and the `app` schema is initialized.
3. **Database Connectivity Test**:
   * Verify Python client connectivity using DevOps CLI:
     ```bash
     uv run python manage.py database connect test
     ```
4. **Migrations & Fixtures Verification**:
   * Run migrations and load fixtures using the wallet connection:
     ```bash
     uv run coffee upgrade
     ```
5. **App Test Suite Validation**:
   * Run the whole test suite:
     ```bash
     make test
     ```
6. **Infrastructure Cleanup Validation**:
   * Stop and wipe the local container, then confirm the already-removed path is idempotent:
     ```bash
     make stop-infra
     make wipe-infra
     make wipe-infra
     ```

### Manual Verification
1. **Expose APEX Dashboard**:
   * Open `https://localhost:8443/ords/apex` in your browser.
   * Verify that the APEX workspace administration login page displays.
   * Log in with username `ADMIN` and password `SuperSecret1` to verify connection.
