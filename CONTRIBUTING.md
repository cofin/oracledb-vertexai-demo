# How to Contribute

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Before you begin

### Sign our Contributor License Agreement

Contributions to this project must be accompanied by a
[Contributor License Agreement](https://cla.developers.google.com/about) (CLA).
You (or your employer) retain the copyright to your contribution; this simply
gives us permission to use and redistribute your contributions as part of the
project.

If you or your current employer have already signed the Google CLA (even if it
was for a different project), you probably don't need to do it again.

Visit <https://cla.developers.google.com/> to see your current agreements or to
sign a new one.

### Review our community guidelines

This project follows
[Google's Open Source Community Guidelines](https://opensource.google/conduct/).

## Development setup and verification

Prerequisites: Python 3.12+, `uv`, Node.js (for Vite frontend assets), `make`,
and a Docker or Podman-compatible container runtime.

1. Install Python dependencies, frontend packages, and compiled Vite assets:

   ```bash
   make install
   uv run python manage.py init
   ```

2. Run static analysis, type checking, and isolated unit tests (no live Oracle
   database required):

   ```bash
   make lint
   make test-unit
   ```

3. Run live Oracle AI Database 26ai integration tests or start the persistent
   **Oracle Autonomous AI Database Free 26ai** container
   (`container-registry.oracle.com/database/adb-free:latest-26ai`, container
   `cymbal-adb-free`, TLS port `1522` with `.envs/tns` mTLS wallet for service
   `myatp_low`, Oracle APEX 26.1.5 + ORDS 26.3 at
   `https://localhost:8443/ords/apex`) and the Litestar server on
   `http://localhost:8000`:

   ```bash
   make start-infra
   uv run coffee upgrade
   make test-integration
   uv run coffee run
   ```

   Setting `ORACLE_CONTAINER_FLAVOR=free` runs lightweight
   `gvenzl/oracle-free:latest` on `:1521/freepdb1` when APEX and ORDS are not
   needed.

4. Build the Sphinx documentation site with warnings treated as errors (does
   not require `vhs`, Playwright, or a running database container):

   ```bash
   make docs
   ```

   When updating Oracle APEX 26.1 `APEXlang` sources under
   `src/apex/cymbal-coffee-ops/` (requires SQLcl `26.1.2+` via
   `make install-sqlcl`) or refreshing demo videos (`docs/_tapes/` and
   `tools/demos/`), validate with:

   ```bash
   make install-sqlcl
   uv run python manage.py infra apex validate --alias cymbal-coffee-ops
   uv run --group demos python manage.py demos check
   make docs-demos-shell
   make docs-demos-web
   ```

## Contribution process

### Code reviews

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult
[GitHub Help](https://help.github.com/articles/about-pull-requests/) for more
information on using pull requests.
