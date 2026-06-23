# Flow: cloudrun-lab-verification-teardown

> Chapter 6 of PRD `cloudrun-gce-lab` (Beads epic `oracledb-vertexai-jw0.6`).
> Depends on Ch3 (`cloudbuild-cloudrun-pipeline`, `oracledb-vertexai-jw0.3`) and
> Ch5 (`cloudrun-lab-authoring`, `oracledb-vertexai-jw0.5`).
> Type: **docs-only**. No source/Terraform/cloudbuild changes; this chapter
> authors documentation prose + paste-ready commands only.

## Specification

### Context

The new Cloud Run lab (`docs/lab-cloud-run.md`, created by Ch5) walks a learner
through `terraform apply` (Ch2/Ch3 Terraform under `tools/deploy/terraform/`)
plus a `gcloud builds submit` deploy. Ch5 ends its walkthrough body but leaves
**two empty section headers as stubs** for this chapter to fill:

- `## Verify your deployment`
- `## Clean up & costs`

This chapter authors the content of those two sections plus a
`### Troubleshooting` subsection nested under `## Verify your deployment`. The
content proves the **Architecture Contract** in `prd.md` actually holds at
runtime — specifically that the app works end-to-end **and** that the Oracle DB
is private (unreachable from the public internet) — and gives a `terraform
destroy` teardown that leaves **zero billable resources**.

All resource names, IPs, IAM roles, and firewall rules below are **copied
verbatim** from the PRD Architecture Contract (`prd.md` lines 89-148). They are
LAW; do not invent or rename anything.

#### Architecture Contract values used by this chapter (source of truth)

| Concern | Value (from `prd.md`) |
|---|---|
| Region / zone | `us-central1` / `us-central1-c` |
| Terraform root | `tools/deploy/terraform/` |
| cloudbuild config | `tools/deploy/gcp/cloudbuild.yaml` |
| VPC | `coffee-vpc` |
| DB subnet | `coffee-subnet` `10.10.0.0/24` |
| Cloud Run egress subnet | `coffee-run-subnet` `10.10.1.0/24` |
| Build-pool peering range | `coffee-buildpool-range` `10.30.0.0/24` |
| DB static internal IP | `coffee-db-ip` = `10.10.0.10` |
| DB VM | `coffee-db` (COS, `e2-standard-4`, `--no-address`, zone `us-central1-c`, tag `coffee-db`) |
| DB data disk | `coffee-db-data` (pd-ssd, 50GB), service name `freepdb1`, port `1521`, user `app` |
| Cloud Run service | `coffee-app` (region `us-central1`, port `8080`) |
| Artifact Registry | `coffee-artifacts` → image `us-central1-docker.pkg.dev/$PROJECT/coffee-artifacts/coffee-app` |
| Build pool | `coffee-build-pool` (peered to `coffee-vpc`) |
| Run SA | `coffee-run-sa@$PROJECT.iam.gserviceaccount.com` |
| Build SA | `coffee-build-sa` (roles/run.admin, roles/iam.serviceAccountUser, roles/artifactregistry.writer, roles/secretmanager.secretAccessor — NO Vertex) |
| DB VM SA | `coffee-db` VM SA (roles/secretmanager.secretAccessor) |
| Firewall (DB ingress) | `coffee-allow-run-to-db`: tcp:1521 from `10.10.1.0/24` **and** `10.30.0.0/24` → tag `coffee-db` |
| Firewall (admin SSH) | `coffee-allow-iap-ssh`: tcp:22 from `35.235.240.0/20` → tag `coffee-db` |
| Secret | `coffee-db-password` (consumed by Cloud Run `--set-secrets`, build migrate step, DB VM cloud-init) |
| Run SA IAM | `roles/aiplatform.user`, `roles/secretmanager.secretAccessor` |
| Run env (key ones) | `VERTEX_AI_PROJECT_ID=$PROJECT`, `VERTEX_AI_LOCATION=us-central1`, `DATABASE_HOST=10.10.0.10` |

#### Cross-chapter write contract (no edit conflict with Ch5)

Ch5 writes `docs/lab-cloud-run.md` and leaves exactly these two top-level
headers, **in this order, at the end of the file, with empty bodies**:

```markdown
## Verify your deployment

## Clean up & costs
```

**This chapter is the ONLY chapter that writes content under those two headers.**
At implement time:

- Find the literal line `## Verify your deployment` and **append** the
  verification body + `### Troubleshooting` subsection **after** it, **before**
  the `## Clean up & costs` line.
- Find the literal line `## Clean up & costs` and **append** the cost note +
  teardown body **after** it (it is the last `##` section in the file).
- **Do NOT** create new `##`-level headers, **do NOT** rename or reorder the two
  stub headers, and **do NOT** touch any content above `## Verify your
  deployment`. If either stub header is missing when this chapter runs, STOP and
  flag a Ch5 contract violation rather than inventing the header.

This makes the boundary unambiguous: Ch5 owns everything above
`## Verify your deployment`; Ch6 owns everything from that line to EOF.

### House voice (match `docs/lab.md`)

- Sphinx/MyST Markdown. Numbered step lists with imperative voice ("Run...",
  "Confirm..."). Fenced ```shell``` blocks for commands; ```text``` for expected
  output. Short bold lead-ins on substeps. No emoji. Address the learner as
  "you". Keep the beginner-friendly tone of the existing lab.
- Commands run in **Cloud Shell** unless explicitly noted otherwise. Cloud Shell
  is **outside** `coffee-vpc` — this is load-bearing for the DB-is-private proof.
- Assume the learner already exported `PROJECT_ID`, `REGION=us-central1`, and
  `ZONE=us-central1-c` earlier in the Ch5 walkthrough (same pattern as
  `docs/lab.md` Step 1). Reuse those env vars; do not re-teach them.

### Requirements

#### Functional (the doc content)

- **FR1 — Verify section.** Author the `## Verify your deployment` body with a
  numbered checklist that proves, in order:
  1. **Cloud Run serves the app** (public HTTPS URL returns HTML).
  2. **A chat query returns a grounded coffee recommendation** (proves Cloud Run
     reached the PRIVATE Oracle DB over Direct VPC egress AND reached Vertex).
  3. **The DB has no external IP** (`accessConfigs` is empty).
  4. **The DB is unreachable from outside the VPC** (a 1521 probe from Cloud
     Shell times out / fails) — and the doc explains *why* (only
     `10.10.1.0/24` + `10.30.0.0/24` are admitted by `coffee-allow-run-to-db`).
  5. **The migration ran from the private build pool** against `10.10.0.10`
     (inspect the last build's `coffee upgrade` step log).
- **FR2 — Troubleshooting subsection.** Author `### Troubleshooting` as a
  symptom → cause → fix matrix grounded in the research risk table
  (`research.md` lines 177-188), covering the six failure classes in Phase 3.
- **FR3 — Cost note.** Author the cost paragraph under `## Clean up & costs`:
  Cloud Run scales to zero, but the COS DB VM (`coffee-db`, `e2-standard-4`) +
  its persistent disk (`coffee-db-data`) are **always on** — the dominant cost;
  call out right-sizing/stopping when idle and that credits burn faster than the
  single-Spot-VM GCE-only lab.
- **FR4 — Teardown.** Author the teardown sequence: drain/note Cloud Run +
  builds, then `cd tools/deploy/terraform && terraform destroy`. Explicitly
  address: persistent disk deletion (intended data loss at teardown), any
  `deletion_protection` / `prevent_destroy` to disable first, Artifact Registry
  images, the reserved internal/peering addresses, and the secret. End with a
  verification that **no billable resource remains**.

#### Non-Functional / constraints

- **NFR1 — Names are LAW.** Every command uses the exact contract identifiers
  above. A wrong region (`us-central1`), zone (`us-central1-c`), IP
  (`10.10.0.10`), service (`coffee-app`), instance (`coffee-db`), or firewall
  name (`coffee-allow-run-to-db`) is a defect.
- **NFR2 — No secret leakage.** No verification or teardown command prints
  `DATABASE_PASSWORD` or the `coffee-db-password` secret value to stdout. The
  chat-query proof must not echo Vertex creds or the DB password.
- **NFR3 — Privacy preserved.** Nothing in verification persists or prints
  browser coordinates; the chat smoke test uses a product/recommendation query,
  not a location-with-coordinates query.
- **NFR4 — Docs-only.** No file under `src/`, `tools/deploy/terraform/`,
  `tools/deploy/gcp/`, or `tools/oracle/` is modified by this chapter. Only
  `docs/lab-cloud-run.md` changes.
- **NFR5 — Paste-ready.** Every command block is copy-paste runnable in Cloud
  Shell with only `PROJECT_ID`/`REGION`/`ZONE` exported. Prefer `gcloud ...
  --format=...` extraction over hand-copied values so the learner never pastes a
  literal IP/URL.
- **NFR6 — Zero orphans.** After the teardown sequence, the documented
  post-destroy check must show no remaining `coffee-*` compute, run, registry,
  address, or secret resources.

### Acceptance criteria

- **AC1 (app works):** Following `## Verify your deployment` against a live
  stack, the Cloud Run URL returns HTTP 200 HTML and a chat query returns a
  grounded coffee recommendation rendered from Oracle rows.
- **AC2 (DB is private):** The `accessConfigs` describe returns empty, and the
  1521 probe from Cloud Shell fails/times out — proving the DB is not publicly
  reachable. The doc explains the firewall admits only the Run egress and build
  pool ranges.
- **AC3 (migration was private):** The learner can confirm the last build's
  `coffee upgrade` step succeeded against `10.10.0.10` from the build log.
- **AC4 (troubleshooting):** The `### Troubleshooting` matrix maps each of the
  six failure classes to a research-grounded cause and a concrete `gcloud` fix.
- **AC5 (cost):** The cost note correctly identifies the always-on DB VM + disk
  as the dominant cost vs. scale-to-zero Cloud Run.
- **AC6 (zero orphans):** Running the teardown sequence on a live stack and then
  the documented post-destroy check shows no surviving `coffee-*` billable
  resources (compute, run, AR image, reserved addresses, secret, disk).
- **AC7 (no conflict):** Content lands only under the two Ch5 stub headers + the
  new `### Troubleshooting` subsection; nothing above `## Verify your
  deployment` is touched; `make docs` / Sphinx build (if run) succeeds.

---

## Implementation Plan

> **Executor note:** This is a docs-only flow. "Tests" here = a verification
> dry-read + (where a live stack exists) running the smoke-test and teardown
> sequences and confirming output. There is no Python TDD. Each phase pairs a
> **verification gate** (what proves the section is correct) with the
> **authoring task**. Author into `docs/lab-cloud-run.md` only.
>
> **Beads:** epic `oracledb-vertexai-jw0.6`. Create one child task per phase
> (titles in the return summary). Attach the relevant contract rows as `bd note`
> context. If the SessionStart banner reports Beads missing/disabled, skip all
> `bd` calls and treat the `- [ ]` markers below as the source of truth.

### Phase 0 — Pre-flight: confirm the Ch5 stub contract

- [ ] 0.1 Open `docs/lab-cloud-run.md` (created by Ch5). Confirm the two literal
  lines `## Verify your deployment` and `## Clean up & costs` both exist with
  empty bodies and are the last two `##` sections, in that order. If either is
  missing or reordered, STOP and flag a Ch5 contract violation (do not author).
- [ ] 0.2 Confirm the walkthrough above defines/exports `PROJECT_ID`,
  `REGION=us-central1`, `ZONE=us-central1-c` (Ch5 owns this). Note the exact env
  var names so Phase 1-4 command blocks reuse them verbatim. Do not redefine them.
- [ ] 0.3 Confirm no other chapter writes under these two headers (grep the repo
  specs for `## Verify your deployment` / `## Clean up & costs`); this chapter is
  the sole writer.

### Phase 1 — Author `## Verify your deployment` (FR1, AC1-AC3)

Append the following body **after** the `## Verify your deployment` line and
**before** `## Clean up & costs`. Use this exact structure and these exact
commands (paste-ready Cloud Shell). Expected-output blocks use ```text```.

- [ ] 1.1 **Intro sentence.** One short paragraph: "These checks prove two
  things at once: the app works end-to-end, and the Oracle database is private —
  reachable by Cloud Run but not by the public internet (including this Cloud
  Shell)."

- [ ] 1.2 **Check 1 — Cloud Run serves the app.** Numbered step. Capture the URL
  into an env var (so later steps reuse it), then curl it:

  ````markdown
  1. **Confirm Cloud Run is serving.** Capture the public service URL and request the home page:

     ```shell
     export RUN_URL=$(gcloud run services describe coffee-app \
       --region us-central1 \
       --format='value(status.url)')
     echo "$RUN_URL"
     curl -s -o /dev/null -w "%{http_code}\n" "$RUN_URL"
     ```

     A `200` response code means the Litestar app booted on Cloud Run and is
     publicly reachable over HTTPS. (A first request may take ~30-60s while a
     cold instance starts and establishes its Direct VPC egress path — see
     Troubleshooting if it hangs.)
  ````

  Include an expected-output ```text``` block showing the `https://coffee-app-...run.app`
  URL on one line and `200` on the next.

- [ ] 1.3 **Check 2 — grounded chat recommendation (proves Run → private DB +
  Vertex).** Numbered step. POST a product query to the chat stream endpoint and
  show that a real coffee recommendation comes back. Prose MUST state this single
  request exercises the whole private path: Cloud Run → `10.10.0.10:1521`
  (Oracle vector search over Direct VPC egress) → Vertex (embeddings/LLM) → grounded
  answer rendered from Oracle rows.

  ````markdown
  2. **Ask the app for a recommendation.** This single request proves the full
     private path works — Cloud Run reaching the **private** Oracle DB at
     `10.10.0.10:1521` for vector search and Vertex AI for embeddings, then
     rendering a grounded answer from Oracle rows:

     ```shell
     curl -sN "$RUN_URL/api/chat/stream" \
       -H "Content-Type: application/x-www-form-urlencoded" \
       --data-urlencode "message=Recommend a smooth cold brew" \
       --data-urlencode "persona=enthusiast" \
       | head -40
     ```

     You should see Server-Sent Event lines (`event: ...` / `data: ...`) ending
     in a `final` event whose payload names a real Cymbal Coffee product. A
     grounded product name (e.g. a real menu item with a price) confirms the
     app reached the private Oracle DB **and** Vertex — if either were
     unreachable the stream would emit an `error` event instead.
  ````

  > Implementer: verify the endpoint path/fields against the live app at
  > implement time. `src/app/domain/chat/controllers/_chat.py` shows
  > `POST /api/chat/stream` returning `ServerSentEvent` with `message` +
  > `persona` form fields and a terminal `final` event. If the deployed contract
  > differs, match the deployed app (the lab walks against the deployed image),
  > and keep the prose claim ("grounded product from the private DB") intact. Do
  > not send any latitude/longitude/coordinate fields (NFR3).

- [ ] 1.4 **Check 3 — DB has no external IP.** Numbered step using the exact PRD
  command; show empty output is the pass condition:

  ````markdown
  3. **Confirm the database VM has no public IP.** Ask Compute Engine for the
     instance's external access configs:

     ```shell
     gcloud compute instances describe coffee-db \
       --zone us-central1-c \
       --format="value(networkInterfaces[0].accessConfigs)"
     ```

     The output is **empty**. An empty `accessConfigs` means `coffee-db` has no
     external IP at all — there is no public address the internet could dial.
  ````

  Expected-output ```text``` block: a single blank line (literally empty).

- [ ] 1.5 **Check 4 — DB is unreachable from outside the VPC.** Numbered step.
  Probe `10.10.0.10:1521` from Cloud Shell and show it fails/times out, then
  explain the firewall. Use a bounded probe so the doc step terminates quickly:

  ````markdown
  4. **Confirm the database port is closed to the outside world.** From Cloud
     Shell — which lives **outside** `coffee-vpc` — try to open a TCP connection
     to the database's private IP and port, with a short timeout:

     ```shell
     timeout 10 bash -c "</dev/tcp/10.10.0.10/1521" \
       && echo "REACHABLE (unexpected!)" \
       || echo "BLOCKED as expected (no route / timeout)"
     ```

     This prints `BLOCKED as expected`. `10.10.0.10` is a **private** address
     inside `coffee-vpc`; Cloud Shell has no route to it, and even with a route
     the `coffee-allow-run-to-db` firewall rule admits `tcp:1521` **only** from
     the Cloud Run egress range `10.10.1.0/24` and the build-pool range
     `10.30.0.0/24` — nothing else. The database is private by construction.
  ````

  Add one explanatory line after the block: optionally inspect the rule with
  `gcloud compute firewall-rules describe coffee-allow-run-to-db --format="yaml(sourceRanges,allowed,targetTags)"`
  to see the two admitted ranges and the `coffee-db` target tag.

- [ ] 1.6 **Check 5 — migration ran from the private build pool.** Numbered step.
  Show how to find the most recent build and confirm its `coffee upgrade` step
  succeeded against `10.10.0.10`:

  ````markdown
  5. **Confirm migrations ran against the private database.** The deploy
     pipeline's migrate step ran `coffee upgrade` from the **private build
     pool** (`coffee-build-pool`), the only Cloud Build path peered into
     `coffee-vpc`. Inspect the most recent build's log:

     ```shell
     BUILD_ID=$(gcloud builds list --region us-central1 --limit=1 \
       --format='value(id)')
     gcloud builds log "$BUILD_ID" --region us-central1 \
       | grep -iE "coffee upgrade|migration|10\.10\.0\.10|SUCCESS" | head -20
     ```

     You should see the `coffee upgrade` step connecting to `10.10.0.10` and a
     `SUCCESS` status for the build. This proves the schema + committed-embedding
     fixtures were applied to the private DB from inside the VPC — no public DB
     exposure was needed.
  ````

  > Implementer: confirm `gcloud builds list/log` accept `--region us-central1`
  > for the private pool at implement time; if the deployed pipeline tags the
  > migrate step differently, adjust the `grep` pattern to match the actual step
  > name Ch3's `cloudbuild.yaml` uses, keeping the `10.10.0.10` + `SUCCESS`
  > evidence.

- [ ] 1.7 **Verification gate (Phase 1):** On a live stack, run checks 1-5 in
  order; AC1 (200 + grounded answer), AC2 (empty accessConfigs + blocked probe),
  AC3 (migrate log) must all pass. If no live stack is available at authoring
  time, dry-read: every command uses only contract names/IPs and exported env
  vars, and each block has a stated pass condition.

### Phase 2 — Author `### Troubleshooting` subsection (FR2, AC4)

- [ ] 2.1 Append a `### Troubleshooting` subsection **immediately after** the
  Phase 1 checklist and **before** `## Clean up & costs`. Open with one line:
  "If a check above failed, find the symptom below." Render as a MyST table
  (`| Symptom | Likely cause | Fix |`). Author exactly these six rows, grounded
  in `research.md` lines 177-188 and the Architecture Contract IAM:

  | # | Symptom | Likely cause | Fix (paste-ready) |
  |---|---------|--------------|-------------------|
  | T1 | Cloud Run returns 5xx or the request hangs ~1 min, then the chat stream errors connecting to the DB | Direct VPC egress **cold-start connection delay** (~1 min while a new instance establishes its VPC path); or `coffee-allow-run-to-db` not admitting `10.10.1.0/24`; or wrong `DATABASE_HOST` env | Retry once the instance is warm. Verify the firewall: `gcloud compute firewall-rules describe coffee-allow-run-to-db --format="yaml(sourceRanges,allowed)"` must list `10.10.1.0/24` + `tcp:1521`. Verify env: `gcloud run services describe coffee-app --region us-central1 --format="value(spec.template.spec.containers[0].env)"` must show `DATABASE_HOST=10.10.0.10`. |
  | T2 | `gcloud builds submit` migrate step hangs or fails to reach the DB | Private pool **not peered** to `coffee-vpc`, missing `servicenetworking` connection, or firewall not admitting the build-pool range `10.30.0.0/24` | Confirm the pool: `gcloud builds worker-pools describe coffee-build-pool --region us-central1`. Confirm the firewall admits the pool range (`coffee-allow-run-to-db` lists `10.30.0.0/24`). Confirm the reserved peering range `coffee-buildpool-range` and the servicenetworking peering exist (`gcloud compute addresses describe coffee-buildpool-range --global` / `gcloud services vpc-peerings list --network=coffee-vpc`). |
  | T3 | `Permission denied` during `gcloud run deploy` (the deploy step of the build) | Build SA missing `roles/run.admin` or `roles/iam.serviceAccountUser` (needed to act-as the run SA) | Grant on the project: `gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:coffee-build-sa@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/run.admin"` and again with `--role="roles/iam.serviceAccountUser"`. |
  | T4 | App or build step fails with a Secret Manager access-denied error | Run SA or build SA missing `roles/secretmanager.secretAccessor`, or the `coffee-db-password` secret has no version | Grant accessor to the failing SA (`coffee-run-sa@...` and/or `coffee-build-sa@...`) on the secret: `gcloud secrets add-iam-policy-binding coffee-db-password --member="serviceAccount:coffee-run-sa@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"`. Confirm a version exists: `gcloud secrets versions list coffee-db-password`. |
  | T5 | Chat returns a Vertex 503 / permission error (app loads but recommendations fail) | Run SA missing `roles/aiplatform.user`, or `VERTEX_AI_PROJECT_ID` unset/placeholder on the service | Grant: `gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:coffee-run-sa@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/aiplatform.user"`. Verify env: the run service must set `VERTEX_AI_PROJECT_ID=$PROJECT_ID` and `VERTEX_AI_LOCATION=us-central1` (check via `gcloud run services describe coffee-app --region us-central1 --format="value(spec.template.spec.containers[0].env)"`). |
  | T6 | Image pull fails / `gcloud run deploy` cannot find the image / push fails | Artifact Registry API not enabled, repo `coffee-artifacts` missing, or build SA missing `roles/artifactregistry.writer` | Enable + verify: `gcloud services enable artifactregistry.googleapis.com`; `gcloud artifacts repositories describe coffee-artifacts --location us-central1`; grant `gcloud artifacts repositories add-iam-policy-binding coffee-artifacts --location us-central1 --member="serviceAccount:coffee-build-sa@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/artifactregistry.writer"`. |

- [ ] 2.2 Add a closing note under the table: most failures are IAM or firewall
  scope, not app code; the app itself is unchanged from the local loop (only
  `DATABASE_HOST` + Vertex env differ). Cross-reference: cold-start (T1) is
  expected behavior, not a bug (cite Direct VPC egress cold-start from research).

- [ ] 2.3 **Verification gate (Phase 2):** Each of T1-T6 names a contract-correct
  resource and a runnable `gcloud` fix; the IAM roles match `prd.md` lines
  141-147 exactly (run SA: aiplatform.user + secretAccessor; build SA:
  run.admin + serviceAccountUser + artifactregistry.writer + secretAccessor, NO
  Vertex). AC4 satisfied.

### Phase 3 — Author cost note under `## Clean up & costs` (FR3, AC5)

- [ ] 3.1 Append, immediately after the `## Clean up & costs` line, a short
  **cost** paragraph (before the teardown steps):

  ````markdown
  Cloud Run **scales to zero** — when no one is using `coffee-app`, it costs
  nothing. The dominant cost in this lab is the database: the `coffee-db` VM
  (an always-on `e2-standard-4`) and its attached persistent disk
  (`coffee-db-data`, a 50GB pd-ssd) bill **continuously**, whether or not anyone
  is using the app. Because that VM never scales to zero, **this lab burns
  credits faster than the single-Spot-VM GCE-only lab.** If you are pausing
  between sessions, stop the VM to cut compute cost (the disk still bills for
  storage):

  ```shell
  gcloud compute instances stop coffee-db --zone us-central1-c
  # ...resume later with:
  gcloud compute instances start coffee-db --zone us-central1-c
  ```

  For a smaller footprint you can right-size the VM (e.g. a smaller machine
  type) in `tools/deploy/terraform/` and re-apply. To stop **all** charges,
  tear the stack down completely with the steps below.
  ````

- [ ] 3.2 **Verification gate (Phase 3):** Cost note names `coffee-db`,
  `e2-standard-4`, `coffee-db-data`, contrasts scale-to-zero Cloud Run vs.
  always-on VM, and the stop/start commands use the correct zone
  `us-central1-c`. AC5 satisfied.

### Phase 4 — Author teardown under `## Clean up & costs` (FR4, NFR6, AC6)

Append after the cost note. The teardown must leave **zero billable resources**.

- [ ] 4.1 **Step 1 — drain Cloud Run + note builds.** Numbered step:

  ````markdown
  1. **Stop new traffic and note the deploy artifacts.** Cloud Run revisions and
     finished builds do not bill for compute once idle, but `terraform destroy`
     removes the service for you. There is nothing to stop manually for Cloud
     Build (builds are ephemeral). You can review what exists before destroying:

     ```shell
     gcloud run services list --region us-central1
     gcloud builds list --region us-central1 --limit=5
     ```
  ````

- [ ] 4.2 **Step 2 — disable delete protection (if Terraform set it).** Numbered
  step. The DB VM is the stateful resource; Terraform may guard it. Tell the
  learner to clear any `deletion_protection` / `prevent_destroy` first:

  ````markdown
  2. **Clear delete protection so the stack can be destroyed.** The database VM
     and disk may be guarded against accidental deletion. If the Terraform config
     sets `deletion_protection = true` on `coffee-db` or a `prevent_destroy`
     lifecycle on the disk/addresses, remove or set those to `false` in
     `tools/deploy/terraform/` and re-apply once, or clear protection directly:

     ```shell
     gcloud compute instances update coffee-db \
       --zone us-central1-c --no-deletion-protection
     ```

     (If no protection was set, this is a harmless no-op.)
  ````

- [ ] 4.3 **Step 3 — `terraform destroy`.** Numbered step. This is the primary
  teardown and removes VM, disk, VPC, subnets, firewall, router/NAT, build pool,
  reserved addresses, Artifact Registry, Cloud Run, IAM, and the secret — because
  all are Terraform-managed (per Locked Decision D5):

  ````markdown
  3. **Destroy the whole stack.** From the Terraform root, destroy every managed
     resource. **This deletes the persistent disk `coffee-db-data` and all
     database data** — that data loss is intended at teardown:

     ```shell
     cd tools/deploy/terraform
     terraform destroy
     ```

     Review the plan and confirm with `yes`. Terraform removes, in dependency
     order: the Cloud Run service `coffee-app`, the Cloud Build private pool
     `coffee-build-pool`, the `coffee-db` VM and its `coffee-db-data` disk, the
     Artifact Registry repo `coffee-artifacts` (and the images in it), the VPC
     `coffee-vpc` with its subnets/firewall/router/NAT, the reserved internal IP
     `coffee-db-ip` and peering range `coffee-buildpool-range`, the IAM
     bindings, and the `coffee-db-password` secret.
  ````

- [ ] 4.4 **Step 4 — sweep any non-Terraform leftovers.** Numbered step. Cover
  the resources most likely to survive a destroy (AR images if the repo wasn't
  empty, the secret if `prevent_destroy`, reserved addresses). Provide explicit
  fallback deletes:

  ````markdown
  4. **Sweep up anything Terraform left behind.** Most resources are gone after
     `terraform destroy`. A few can linger if they were created outside Terraform
     or guarded — delete them explicitly so nothing keeps billing:

     ```shell
     # Artifact Registry images (if the repo or images outlived the repo resource)
     gcloud artifacts repositories delete coffee-artifacts \
       --location us-central1 --quiet 2>/dev/null || true

     # Reserved addresses (regional internal IP + global peering range)
     gcloud compute addresses delete coffee-db-ip \
       --region us-central1 --quiet 2>/dev/null || true
     gcloud compute addresses delete coffee-buildpool-range \
       --global --quiet 2>/dev/null || true

     # The DB password secret
     gcloud secrets delete coffee-db-password --quiet 2>/dev/null || true
     ```
  ````

  > Implementer: keep these as idempotent best-effort deletes (`|| true`) since
  > `terraform destroy` normally handles them; they exist so a partially-applied
  > or drifted stack still tears down to zero. Match `--global` vs `--region`
  > to how Ch2/Ch3 reserved each address (`coffee-db-ip` is regional internal in
  > `coffee-subnet`; `coffee-buildpool-range` is a `--global --purpose=VPC_PEERING`
  > range per `prd.md` line 103). If Ch2/Ch3 reserved them differently, match the
  > Terraform.

- [ ] 4.5 **Step 5 — confirm zero billable resources remain.** Numbered step.
  The post-destroy proof for AC6/NFR6:

  ````markdown
  5. **Confirm nothing is left.** Each command below should return **no
     `coffee-*` rows**:

     ```shell
     gcloud compute instances list        --filter="name~^coffee-"
     gcloud compute disks list            --filter="name~^coffee-"
     gcloud compute addresses list        --filter="name~^coffee-"
     gcloud compute networks list         --filter="name~^coffee-"
     gcloud run services list --region us-central1 --filter="metadata.name~^coffee-"
     gcloud artifacts repositories list --location us-central1 --filter="name~coffee-"
     gcloud builds worker-pools list --region us-central1 --filter="name~coffee-"
     gcloud secrets list --filter="name~coffee-"
     ```

     Empty output across the board means the stack is fully torn down and nothing
     is billing. You can now safely close the lab.
  ````

- [ ] 4.6 **Verification gate (Phase 4):** On a live stack, run Steps 1-5;
  `terraform destroy` exits 0 and the Step 5 sweep returns no `coffee-*`
  resources (AC6). No command prints the secret value (NFR2). All names/zones/
  regions match the contract (NFR1).

### Phase 5 — Cross-section consistency + review (AC7)

- [ ] 5.1 Re-read the whole `## Verify your deployment` → `### Troubleshooting`
  → `## Clean up & costs` span for house-voice consistency with `docs/lab.md`
  (numbered imperative steps, ```shell``` fences, bold lead-ins, no emoji).
- [ ] 5.2 Confirm nothing above `## Verify your deployment` was modified (Ch5's
  content is untouched); the only structural additions are the two stub bodies
  and the one `### Troubleshooting` subsection (AC7).
- [ ] 5.3 Grep the authored span for stray/incorrect identifiers: every resource
  name, IP, region, zone, IAM role matches the contract table at the top of this
  spec. No placeholder like `<VM-IP>` survives; IPs are the literal `10.10.0.10`
  / `10.10.1.0/24` / `10.30.0.0/24`.
- [ ] 5.4 If Sphinx/MyST builds locally (`make docs` or the repo's docs target),
  build `docs/` and confirm `lab-cloud-run.md` renders without warnings on the
  new sections (tables, fenced blocks). If no docs target exists, skip with a note.
- [ ] 5.5 Dispatch `code-reviewer` (or `flow:code-reviewer`) on the diff of
  `docs/lab-cloud-run.md` to validate: names match the contract, commands are
  paste-ready, no secret leakage, no edit conflict with Ch5, AC1-AC7 covered.
- [ ] 5.6 Update `.agents/flows.md` chapter status for this flow and sync Beads
  (`flow-sync`) so `spec.md` markers and Beads agree. Skip the Beads half if the
  backend is reported missing/disabled.

### Out of scope (explicitly)

- Writing `docs/lab-cloud-run.md`'s walkthrough body, prerequisites, or the two
  stub headers themselves — that is Ch5 (`cloudrun-lab-authoring`).
- Any change to Terraform (`tools/deploy/terraform/`), `cloudbuild.yaml`
  (`tools/deploy/gcp/`), the Dockerfile, `tools/oracle/`, or `src/` — those are
  Ch1/Ch2/Ch3.
- The GCE-only lab (`docs/lab-gce.md`) and the `docs/lab.md` index — Ch4
  (`lab-gce-rename`).
- Adding a GitHub-push auto-trigger or remote Terraform state — PRD challenges
  only, not core verification/teardown.
