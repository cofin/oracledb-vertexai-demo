# Flow Spec: apex-media-staging (Chapter 1)

*Beads: `oracledb-vertexai-apxg.1` (chapter epic)*
*Parent PRD: [../apex-gvenzl-install/prd.md](../apex-gvenzl-install/prd.md)*
*Research: [../../research/research_apex_upgrade/](../../research/research_apex_upgrade/)*
*Status: Done — 5/5 tasks closed; 32 unit tests green (ruff + mypy clean); commits 56cb007..1c157c6*

---

## 1.0 Context

The reverted `gvenzl/oracle-free` container bundles neither APEX nor ORDS, so APEX media must be acquired
and staged on the host before any install (Ch2) or ORDS image serving (Ch3) can run. The APEX full
release is a **public, no-login download** from OTN
(`https://download.oracle.com/otn_software/apex/apex_<ver>.zip`, verified HTTP 200), so acquisition is
fully automatable. This chapter delivers a version-parameterized, idempotent media pipeline and a defined
staging layout that downstream chapters mount/consume. It performs **no database changes**.

---

## 2.0 Requirements

- Download `apex_<ver>.zip` (default version **26.1**) from the public OTN URL; no Oracle login.
- Parameterize the version and the zip variant (English `apex_<ver>_en.zip` default vs full `apex_<ver>.zip`).
- Cache per version on the host under a gitignored path; never re-download a valid cached zip.
- Verify integrity before use: HTTP size sanity + `zip -T`/`unzip -t` and presence of `apex/apexins.sql`
  after extraction. Fail loudly on corruption (no silent fallback).
- Extract to a stable layout exposing the `apex/` tree (including `apex/images/`).
- Expose the resolved host paths + container mount specs as data for Ch2 (install scripts) and Ch3
  (ORDS `/i/` images) to consume — this chapter does **not** start containers or mount anything itself.
- Idempotent and re-runnable; a `--force` re-download/re-extract path.

---

## 3.0 Proposed Changes

### Component: APEX media pipeline (`tools/oracle/`)

#### [CREATE] `tools/oracle/apex_media.py`
- `@dataclass ApexMediaConfig`:
  - `version: str = "26.1"`, `english_only: bool = True`.
  - `cache_root: Path = tools/oracle/downloads/apex` (host cache; gitignored).
  - `base_url: str = "https://download.oracle.com/otn_software/apex"`.
  - Derived: `filename` (`apex_<ver>_en.zip` or `apex_<ver>.zip`), `url`, `version_dir`
    (`<cache_root>/<ver>`), `extracted_apex_dir` (`<version_dir>/apex`), `images_dir`
    (`<extracted_apex_dir>/images`).
  - `from_env()` honoring `APEX_VERSION` / `APEX_ENGLISH_ONLY` (floor-only, quiet defaults).
- `class ApexMedia`:
  - `ensure(*, force: bool = False) -> ApexMediaPaths` — orchestrates download → verify → extract,
    idempotent; returns resolved paths.
  - `download(*, force)` — streamed download with progress; skip when a valid zip exists; validate
    `Content-Length` vs received bytes.
  - `verify_zip()` — integrity check (`zipfile.testzip()`); confirm `apex/apexins.sql` member exists.
  - `extract(*, force)` — extract into `version_dir`; skip when `apex/apexins.sql` already present.
  - `paths()` / `ApexMediaPaths` (frozen) — `apex_dir`, `images_dir`, `apexins`, `version`.
  - `container_mounts(*, db_target, ords_images_target)` — returns `-v host:container` mount specs
    (data only; consumed by Ch2/Ch3, not applied here).
- Use `urllib`/`httpx` already in the dependency set; Rich console progress consistent with
  `tools/oracle/database.py`.

#### [MODIFY] `.gitignore`
- Add `tools/oracle/downloads/` (cached APEX zips + extracted media must not be committed).

> No changes to `database.py` run command in this chapter — mount wiring lands in Ch2/Ch3 against the
> reverted gvenzl `_build_run_command()`. This chapter only provides `container_mounts()` as the contract.

---

## 4.0 Implementation Plan (TDD)

- [x] **Task 1.1** — `ApexMediaConfig` + URL/filename/path derivation (version + english_only),
  `from_env()`. Unit tests assert URLs/paths for `26.1` (en + full) and a future version. `[56cb007]`
- [x] **Task 1.2** — Idempotent `download()` with size validation and `--force`; skip-on-valid-cache.
  Unit tests mock the HTTP layer (success, truncated/size-mismatch → raise, cache-hit → no fetch). `[ed0126d]`
- [x] **Task 1.3** — `verify_zip()` + `extract()` with `apexins.sql` presence gate and skip-on-extracted.
  Unit tests use a tiny synthetic zip fixture (good + corrupt + missing-apexins). `[81a57c6]`
- [x] **Task 1.4** — `paths()` / `ApexMediaPaths` + `container_mounts()` contract; `.gitignore` entry.
  Unit tests assert the mount-spec shape and resolved absolute paths. `[57f16c6]`
- [x] **Task 1.5** — `ApexMedia.ensure()` orchestration (download→verify→extract→paths), idempotent
  end-to-end. Unit test runs twice; second run performs no network/extract work. `[1c157c6]`

---

## 5.0 Verification Plan

### Automated
```bash
uv run pytest src/tests/unit/tools/oracle/test_apex_media.py
make lint
```
- All `apex_media` unit tests deterministic (no real network; HTTP + filesystem mocked/synthetic zip).

### Manual (real media smoke — optional, network-dependent)
```bash
uv run python - <<'PY'
from tools.oracle.apex_media import ApexMedia, ApexMediaConfig
paths = ApexMedia(ApexMediaConfig(version="26.1")).ensure()
print("apex_dir:", paths.apex_dir, "exists:", paths.apexins.exists())
PY
```
- Confirms a real download+extract yields `apex/apexins.sql`; a second run is a no-op (idempotent).

---

## 6.0 Definition of Done

- `ApexMedia.ensure()` reliably produces a verified, extracted APEX 26.1 tree under
  `tools/oracle/downloads/apex/26.1/apex/` with `images/` present.
- Re-running is a no-op; `--force` re-fetches/re-extracts; corruption fails loudly.
- `container_mounts()` returns the mount contract Ch2/Ch3 will consume.
- `tools/oracle/downloads/` is gitignored; `make lint` and the new unit tests pass.
