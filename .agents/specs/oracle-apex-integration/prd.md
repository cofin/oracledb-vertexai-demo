# Master PRD: Oracle APEX 26.1 & Autonomous Database Container Migration

*PRD ID: `oracle-apex-integration`*
*Created: 2026-06-13*
*Status: Completed - runtime verification passed 2026-06-13*

---

## North Star

Migrate the local development database infrastructure from standard `gvenzl/oracle-free` to the official Oracle Autonomous Database Free container (`container-registry.oracle.com/database/adb-free:latest-26ai`). This transition enables out-of-the-box support for Oracle APEX 26.1 and Oracle REST Data Services (ORDS) while preserving full architectural parity with real production Autonomous Database deployments by using **Mutual TLS (mTLS) with signed wallet details** locally.

---

## Reviewed Sources

### `tools/oracle/database.py`
- Declares `DatabaseConfig` for container image, ports, hostname, and environment variables.
- Current branch uses `container-registry.oracle.com/database/adb-free:latest-26ai`.
- Maps Oracle wallet, data, audit, ORDS/APEX HTTPS, TLS, mTLS, and Mongo API ports for the ADB Free container.
- No longer relies on `/container-entrypoint-initdb.d` or `/container-entrypoint-startdb.d` mounts for app schema creation.

### `tools/oracle/connection.py`
- Implements `ConnectionConfig` and `ConnectionTester` classes.
- Detects deployment mode (`managed` vs `external`).
- Connects using standard `oracledb.connect()`.
- Supports database wallet setup if `wallet_location` is present in configuration (via `TNS_ADMIN`) and passes `config_dir` for thin-mode wallet connections.
- Bounces database during tests by resetting and setting `TNS_ADMIN`.

### `src/app/lib/settings.py` (DatabaseSettings)
- Contains settings for local and autonomous connection parameters.
- If `is_autonomous` is True (wallet configured), it resolves DSN via parsed URL and applies `TNS_ADMIN` path configurations.
- If `is_autonomous` is False, it falls back to standard TCP connection parameters (port `1521`, service name `myatp_low`).

---

## Product Decisions

1. **Leverage the Pre-Configured Container**: Switch the development container image from `gvenzl/oracle-free` to `container-registry.oracle.com/database/adb-free:latest-26ai` to avoid the Oracle SSO authentication wall for downloading and installing APEX 26.1 manually.
2. **Support Signed Wallet Authentication (mTLS) via Direct Bind-Mount**:
   - Establish connection parity with OCI production environments.
   - Map both port `1521` (one-way TLS) and port `1522` (mTLS) to the host.
   - Map a host directory `.envs/tns` to `/u01/app/oracle/wallets/tls_wallet:z` directly in the `docker/podman run` command.
   - During the database container's initial boot, the container engine writes the generated client credentials wallet directly to the mounted host directory `.envs/tns`.
   - This eliminates the need to run copy commands (`docker cp` / `podman cp`) and ensures that the client application connects natively via `TNS_ADMIN` out of the box.
3. **Automate Post-Startup User Initialization**:
   - The Autonomous container does not automatically create custom development users (like the `app` user) or support mounted `/entrypoint` SQL scripts.
   - We will automate this by adding a post-startup SQL execution step after `tools/oracle/database.py:wait_for_healthy()` succeeds:
     - Connect as `ADMIN` using the newly written local wallet to execute DDL statements creating the `app` user and granting resource/developer privileges.
4. **Preserve DevOps Interface**: Keep developer CLI interfaces (`make start-infra`, `uv run coffee upgrade`, `manage.py infra start`) transparent. Raw SQLSpec developer commands remain on `python manage.py database ...`.

---

## Roadmap

### Chapter 1 - `adb-container-lifecycle`

Configure the container orchestration to deploy the official Oracle Autonomous Database Free container with APEX 26.1 and ORDS, and handle wallet generation.

**Deliverables:**
- Modify [tools/oracle/database.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/tools/oracle/database.py):
  - Change default image to `container-registry.oracle.com/database/adb-free:latest-26ai`.
  - Add `--cap-add SYS_ADMIN` and `--device /dev/fuse` to container run flags (required by the OCI Autonomous container).
  - Map ports:
    - Host `1521` to Container `1522` (TLS entrypoint).
    - Host `1522` to Container `1522` (mTLS entrypoint).
    - Host `8443:8443` (APEX/Database Actions HTTPS web portal).
    - Host `27017:27017` (MongoDB API).
  - Map host data storage to `/u01/data:z` and Oracle datafiles to `/u01/app/oracle/oradata:z`.
  - Map environment variables `ADMIN_PASSWORD` and `WALLET_PASSWORD` (mapping both to `SuperSecret1` by default).
  - Read `DATABASE_USER` and `DATABASE_PASSWORD` for the application schema user.
  - Add host-to-container volume mount:
    - Bind mount host folder `.envs/tns` to `/u01/app/oracle/wallets/tls_wallet:z`.
  - Disable mounting of `/container-entrypoint-initdb.d` and `/container-entrypoint-startdb.d` folder volumes, as `adb-free` does not support these setup directories.
- Modify [tools/cli/doctor.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/tools/cli/doctor.py):
  - Add a check for allocated Docker/Podman memory to warn the developer if host memory allocation is below the required **8 GiB**.

---

### Chapter 2 - `post-startup-user-initialization`

Initialize the development schemas/roles using the automatically generated local wallet once the database container reports healthy.

**Deliverables:**
- Modify [tools/oracle/database.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/tools/oracle/database.py):
  - Create a new script/SQL execution routine called `initialize_db_users()` that runs immediately after the container becomes healthy:
    - Set `os.environ["TNS_ADMIN"]` to the absolute path of `.envs/tns` on the host.
    - Connect to the local database as `ADMIN` using the newly written wallet on the `myatp_low` service:
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
    - Execute DDL commands to create the `app` user (if not exists) and grant standard database development privileges:
      ```sql
      CREATE USER app IDENTIFIED BY "SuperSecret1";
      GRANT CONNECT, RESOURCE, DB_DEVELOPER_ROLE TO app;
      GRANT UNLIMITED TABLESPACE TO app;
      ```

---

### Chapter 3 - `client-env-alignment`

Configure connection settings to support wallet-based connections by default for local development.

**Deliverables:**
- Modify [tools/lib/utils.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/tools/lib/utils.py):
  - Update `create_env_interactive()` for `managed` mode:
    - Default `DATABASE_URL` to `oracle+oracledb://app:SuperSecret1@myatp_low`.
    - Default `DATABASE_USER` to `app` and `DATABASE_PASSWORD` to `SuperSecret1`.
    - Default `WALLET_PASSWORD` to `SuperSecret1`.
    - Default `WALLET_LOCATION` (or `TNS_ADMIN`) to `./.envs/tns`.
    - Default `DATABASE_SERVICE_NAME` to `myatp_low`.
- Modify [src/app/lib/settings.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/src/app/lib/settings.py):
  - Ensure that `WALLET_LOCATION` is converted to an absolute path when resolving, preventing working directory alignment mismatches between application boot, tests, and CLI tasks.

---

## Global Constraints

- **Code Preservation**: Do not alter or recreate existing wallet configuration tools (`tools/oracle/wallet.py` or the `wallet` CLI group) since they are still required when running in external/production Cloud environments.
- **TDD Verification**: Ensure that the AnyIO database connection tests and schema migrations continue to run successfully on the new local container setup.
- **Docker Resources**: The developer is responsible for allocating sufficient CPU/RAM on their host machine for the container.

---

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| **Resource constraints**: Developer machines crash or fail to start the container due to low memory. | The `doctor` command will run check diagnostics and alert developers if Docker Engine memory limits are set below 8 GiB. |
| **Path mismatches**: Connections fail because relative paths inside `TNS_ADMIN` do not resolve depending on shell execution context. | Force-resolve the `WALLET_LOCATION` path to an absolute filesystem path within `settings.py` before assigning it to `os.environ["TNS_ADMIN"]`. |
| **Migration failure**: Migrations fail because the `app` user schema hasn't been created on database start. | The post-start initialization script will block `make start-infra` completion until the wallet has been extracted and the `app` user schema has been successfully created. |

---

## Acceptance Criteria

- `make start-infra` starts the `container-registry.oracle.com/database/adb-free:latest-26ai` container, waits for health checks, writes the wallet files to `.envs/tns` automatically, creates the `app` schema, and returns exit code 0.
- Running `docker ps` shows ports `1521` (TLS), `1522` (mTLS), and `8443` (APEX/ORDS HTTPS) are correctly mapped to the host.
- The `app` user schema and database privileges are created automatically upon start-infra.
- Running `uv run coffee upgrade` runs migrations and fixture loading successfully against `myatp_low` using the extracted local credentials wallet.
- Running `make stop-infra` stops the container, and `make wipe-infra` removes it and remains successful when the container is already gone.
- Contributor can log into the APEX administration dashboard by opening `https://localhost:8443/ords/apex` in their browser.

---

## Review Questions

1. Do you prefer the default wallet extraction location to be `.envs/tns` (matching the default location for external database setups), or should we place it under a dedicated directory like `.wallet/`? (We recommend `.envs/tns` to keep path variables consistent across local and external modes).
