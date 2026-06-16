# Flow: oraclelinux-podman-lab

*Chapter 2 of PRD `adb-podman-lab-hardening` (Beads epic `oracledb-vertexai-9p5.2`)*
*Blocked by Chapter 1 (`9p5.1`): the lab must document a runtime validated on podman/OL.*
*Source: `.agents/research/research_adb_hooks_ux_lab/research.md` (Part 3)*

## Specification

Rewrite `tools/scripts/lab.md` as a **single canonical Oracle Linux 9 + rootless podman** workshop (drop the Ubuntu/docker track entirely) and correct every verified factual defect. Audience: Oracle users. Doc-only changes except the illustrative BigQuery snippet.

## Verified platform reference (use these exact commands)

- **VM image:** `--image-project=oracle-linux-cloud --image-family=oracle-linux-9` (Oracle builds/supports these on GCE; no license fee).
- **Podman:** `sudo dnf install -y container-tools git curl` (OL9 ships container-tools as a metapackage; `ol9_appstream` enabled by default).
- **Build deps:** `sudo dnf -y groupinstall "Development Tools"`.
- **Node 20:** `sudo dnf module enable -y nodejs:20 && sudo dnf install -y nodejs`.
- **Rootless:** no `usermod -aG docker`; add `loginctl enable-linger $USER` only if a persistent rootless service is needed.
- **Verified data:** `product.json.gz` = 130 products (108 `category=coffee`), `store.json.gz` = 17 stores.
- **Verified model/port:** embedding `gemini-embedding-2-preview` (`settings.py:349`); app on `5006` (`-L8080:localhost:5006`).

## Code Analysis Summary

- `tools/oracle/container.py:46-73` — `detect_runtime()` already supports podman (falls back when docker absent); the CLI needs no change for podman.
- `tools/oracle/database.py:768-777` — bind mounts already use `:z` SELinux relabels; `--cap-add SYS_ADMIN` + `--device /dev/fuse` present (validated under podman in Ch1).
- `Makefile:85` — `make install` already runs `assets build` (Step 7.2 build is redundant).
- `src/app/domain/system/services/services.py:131` — `CacheService(OracleAsyncService)`; no Valkey/Redis anywhere.

## Implementation Plan

### Phase 1: Platform rewrite — Steps 1-4 (`9p5.2.1`)
- [ ] 1.1 Step 3 VM (`lab.md:99-113`): swap the Ubuntu image for `oracle-linux-cloud` / `oracle-linux-9`.
- [ ] 1.2 Step 4 (`lab.md:136-189`): drop the `needrestart` sed (`:139`); replace `apt` with `dnf`; install podman/build-tools/node per the platform reference; remove `usermod -aG docker` (`:181`).

### Phase 2: docker → podman + infra verification (`9p5.2.2`)
- [ ] 2.1 Step 6.1 (`lab.md:219-224`): remove the "alongside a Valkey caching instance" claim.
- [ ] 2.2 Step 6.2 (`:227-230`): verify the single Oracle container; `docker ps` (`:230`) → `podman ps`. Sweep all remaining `docker` → `podman`.

### Phase 3: Factual fixes (`9p5.2.3`)
- [ ] 3.1 Counts → "130 products and 17 store locations" (intro `:5`, Step 6.3 `:233-237`); fix the same in `README.md`.
- [ ] 3.2 Embedding model → `gemini-embedding-2-preview` (`:5`).
- [ ] 3.3 Step 7.4 third bullet (`:262`): "Cosine or Euclidean distances" → "cosine similarity scores".

### Phase 4: Localization + maintainable snippets (`9p5.2.4`)
- [ ] 4.1 Translate Challenge 2 Step A (`lab.md:545-550`) to English.
- [ ] 4.2 Convert the Challenge 1 `_chat.py` (`:307-537`) and Challenge 2 `_pages.py`/`renderStoreCard` (`:564-663`) whole-file drop-ins into targeted inserted snippets; keep verified anchors (`base.html.j2:19`, `main.js:713`, `settings.maps.embed_enabled`, `settings.maps.EMBED_API_KEY`).

### Phase 5: Example correctness + redundancy + dry run (`9p5.2.5`)
- [ ] 5.1 Fix the BigQuery example (`:501-515`): inspect `insert_rows_json` errors; log via `logger.aexception`/`awarning`, not `print`; don't discard the executor future.
- [ ] 5.2 Remove the redundant `assets build` in Step 7.2 (`:253-256`); keep it in Challenge 2 Step E (`:666-670`). Confirm `5006` mapping.
- [ ] 5.3 Dry-run the full rewritten lab on a fresh OL9 VM with podman → working `/explore`.

### Verification Gate
- [ ] No `apt`/`docker`/`needrestart`/`Valkey` references remain; counts/model/port correct.
- [ ] Fresh OL9 + podman dry-run reaches `/explore`; `make lint`/`make test` unaffected.
- [ ] Update Beads task states and reconcile the markdown view.
