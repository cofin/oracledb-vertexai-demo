# Hands-on Lab (Single-VM GCE): Cymbal Coffee — Oracle 26ai + Vertex AI

This is the **all-in-one** path: **Oracle Autonomous AI Database Free 26ai** (`adb-free:latest-26ai`, pre-bundling **Oracle APEX 26.1.5 + ORDS 26.3**) and the **Litestar 2** web application (`http://localhost:8000`) run together on a single Compute Engine VM — the fastest way to explore Hybrid Reciprocal Rank Fusion, Vertex AI agentic chat, and Oracle APEX 26.1 Generative AI Services end to end. Want a production-shaped split (Cloud Run + a private GCE Oracle DB + Cloud Build)? Follow the [Cloud Run lab](lab-cloud-run.md) instead.

Welcome to the **Cymbal Coffee Hands-on Lab**. In this workshop, you will provision, configure, seed, and run an AI-powered specialty coffee recommendation and store-operations platform. For complete background concepts and reference material, visit the [Cymbal Coffee Documentation Site](https://cofin.github.io/oracledb-vertexai-demo/index.html).

The application combines **Oracle AI Database 26ai** Hybrid Reciprocal Rank Fusion (`CTXSYS.CONTEXT` `MULTI_COLUMN_DATASTORE` + HNSW `VECTOR(3072, FLOAT32)` `FETCH APPROX`), **Google Cloud Vertex AI** (`gemini-embedding-2` + `gemini-3.8-flash`), **Oracle APEX 26.1** (`APEX_AI.GENERATE` + **ORDS 26.3**), **SQLSpec `0.69.0`**, and the native **`AgentRuntime`** (`app.domain.ai`). The web frontend is built on [**Litestar 2**](https://docs.litestar.dev/), [**HTMX**](https://htmx.org/), and [**Jinja templates**](https://jinja.palletsprojects.com/), wired with [**Dishka Dependency Injection**](https://dishka.readthedocs.io/) and served on HTTP port `8000` by the [**Granian**](https://github.com/emmett-framework/granian) ASGI server via [`litestar-granian`](https://github.com/cofin/litestar-granian).

---

## Prerequisites & Audience Expectations

+ **GCP Knowledge**: None. This lab is designed to be beginner-friendly for Google Cloud Platform.
+ **Tools Required**: A web browser and access to a Google Cloud Console account with billing or workshop credits enabled.

---

## Step 1: Google Cloud Platform Environment Setup

Initialize your cloud workspace and enable the required APIs for Compute Engine, Identity-Aware Proxy, Vertex AI, and Maps backends.

1. Log into the **Google Cloud Console** (`https://console.cloud.google.com`) using your workshop credentials.
2. In the top navigation bar, click the **Activate Cloud Shell** icon (a small terminal icon `>_`). Wait a few moments for the persistent Linux terminal environment to provision and connect.
3. Set your active project using the following command (replace `[YOUR-PROJECT-ID]` with your actual GCP project ID shown on your console dashboard):

   ```shell
   gcloud config set project [YOUR-PROJECT-ID]
   ```

4. Define the default geographic deployment region and zone:

   ```shell
   export REGION=us-central1
   export ZONE=us-central1-c
   export PROJECT_ID=$(gcloud config get-value project)
   export USER=<Your provided user e.g. devstarxxxx@gcplab.me>

   gcloud config set compute/region $REGION
   gcloud config set compute/zone $ZONE
   ```

5. Enable the Google Cloud Services APIs for Compute Engine, Identity-Aware Proxy, Vertex AI, and Maps backends:

   ```shell
   gcloud services enable compute.googleapis.com \
                          iap.googleapis.com \
                          aiplatform.googleapis.com \
                          maps-embed-backend.googleapis.com \
                          osconfig.googleapis.com
   ```

---

## Step 2: Networking and Security Configuration

To keep your virtual machine private while permitting terminal and browser access, use Identity-Aware Proxy (IAP) for authenticated SSH tunnels without exposing a public IP address on the VM.

1. Create a firewall rule allowing incoming SSH traffic from the Google IAP proxy CIDR block:

   ```shell
   gcloud compute firewall-rules create allow-ssh-ingress-from-iap \
     --network=default \
     --direction=INGRESS \
     --action=allow \
     --rules=tcp:22 \
     --source-ranges=35.235.240.0/20
   ```

2. Bind the IAP tunnel resource accessor role to your cloud user account:

   ```shell
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="user:$USER" \
     --role="roles/iap.tunnelResourceAccessor"
   ```

3. Create a Cloud Router for outbound internet requests (required to download OS packages, Oracle SQLcl, and container images):

   ```shell
   gcloud compute routers create default-router --network=default
   ```

4. Provision a Cloud NAT gateway associated with the router so the private VM can reach outbound HTTPS endpoints without an external IP:

   ```shell
   gcloud compute routers nats create default-nat-gw \
     --router=default-router \
     --auto-allocate-nat-external-ips \
     --nat-all-subnet-ip-ranges \
     --enable-logging
   ```

---

## Step 3: Compute Engine Virtual Machine Provisioning

Provision a Compute Engine virtual machine where the Autonomous AI Database Free 26ai container (`cymbal-adb-free`) and the Litestar web application run side by side.

1. Run the following command in Cloud Shell to create an `e2-standard-4` (4 vCPUs, 16 GB RAM) Ubuntu 26.04 LTS virtual machine with a 100 GB balanced persistent disk:

   ```shell
   gcloud compute instances create coffeevm \
     --project=$PROJECT_ID \
     --machine-type=e2-standard-4 \
     --zone=$ZONE \
     --network-interface=stack-type=IPV4_ONLY,subnet=default,no-address \
     --metadata=enable-osconfig=TRUE,enable-oslogin=true \
     --no-restart-on-failure \
     --maintenance-policy=TERMINATE \
     --provisioning-model=SPOT \
     --instance-termination-action=STOP \
     --scopes=https://www.googleapis.com/auth/cloud-platform \
     --tags=xe \
     --create-disk=auto-delete=yes,boot=yes,device-name=coffeevm,image=projects/ubuntu-os-cloud/global/images/family/ubuntu-2604-lts-amd64,mode=rw,size=100,type=pd-balanced
   ```

2. Grant the Compute Engine default service account permission to invoke Vertex AI models (`gemini-embedding-2` and `gemini-3.8-flash`):

   ```shell
   PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   ```

---

## Step 4: Connect to the VM and Install Core OS Packages

Connect to the virtual machine over IAP and install Docker, Git, Node.js 24, a headless Java runtime (for Oracle SQLcl `26.1.2+`), and Python build utilities.

1. Establish an SSH session into the VM via the IAP tunnel:

   ```shell
   gcloud compute ssh --zone "$ZONE" "coffeevm" --tunnel-through-iap --project $PROJECT_ID
   ```

2. Configure `needrestart` to restart background services non-interactively during package upgrades:

   ```shell
   sudo sed -i "s/#\$nrconf{restart} = 'i';/\$nrconf{restart} = 'a';/g" /etc/needrestart/needrestart.conf
   ```

3. Refresh the `apt` package index and remove any preinstalled Node.js packages to avoid version conflicts:

   ```shell
   sudo apt update
   sudo apt purge -y nodejs npm libnode-dev
   sudo apt autoremove -y
   ```

4. Install Docker, compilation utilities, a Java runtime (required by SQLcl `26.1.2+` for APEXlang commands), Python venv support, Git, and `curl`:

   ```shell
   sudo apt install -y docker.io docker-compose-v2 build-essential default-jre-headless python3.14-venv git curl
   ```

5. Register and install the NodeSource Node.js v24 distribution:

   ```shell
   curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
   sudo apt install -y nodejs
   ```

6. Add your Linux user to the `docker` group so container commands run without `sudo`:

   ```shell
   sudo usermod -aG docker $USER
   ```

7. **Reconnect to apply group membership**: Exit the VM session and reconnect so the `docker` group takes effect:

   ```shell
   exit
   gcloud compute ssh --zone "$ZONE" "coffeevm" --tunnel-through-iap --project $PROJECT_ID
   ```

---

## Step 5: Clone Repository, Install Toolchain, and Configure `.env`

1. Clone the repository and enter the project root directory:

   ```shell
   git clone https://github.com/cofin/oracledb-vertexai-demo.git
   cd oracledb-vertexai-demo/
   ```

2. Run `make install` (which installs `uv`, creates the Python 3.12 virtual environment, syncs dependencies including **SQLSpec `0.69.0`**, and builds the Vite frontend bundle) followed by `make install-sqlcl` (which idempotently installs Oracle SQLcl `26.1.2+` into `~/.local/bin` for APEX 26.1 APEXlang validation, import, and export):

   ```shell
   export PATH=$PATH:~/.local/bin
   make install
   make install-sqlcl
   ```

3. Initialize `.env` using the interactive project initializer:

   ```shell
   uv run python manage.py init
   ```

   Follow the prompts for the managed Autonomous AI Database Free 26ai container:
   + **Deployment mode**: `managed`
   + **`SECRET_KEY`**: press Enter to auto-generate
   + **`GOOGLE_PROJECT_ID`**: enter your GCP project ID (this populates `GOOGLE_PROJECT_ID` and `VERTEX_AI_PROJECT_ID=${GOOGLE_PROJECT_ID}` with `VERTEX_AI_LOCATION=global`)
   + **Database settings**: accept the defaults (`DATABASE_USER=app`, `DATABASE_PASSWORD=SuperSecret1`, `DATABASE_URL=myatp_low`, `WALLET_LOCATION=./.envs/tns`, `WALLET_PASSWORD=SuperSecret1`)

   The generated `.env` configures Granian on `LITESTAR_HOST=0.0.0.0` and `LITESTAR_PORT=8000`.

---

## Step 6: Start Autonomous AI Database Free 26ai (`adb-free:latest-26ai`) and Load Fixtures

1. Start the local Oracle 26ai infrastructure container:

   ```shell
   make start-infra
   ```

   Under the hood, `make start-infra` runs `uv run python manage.py infra start`, which:
   + Pulls and starts `container-registry.oracle.com/database/adb-free:latest-26ai` as container **`cymbal-adb-free`** backed by persistent volume **`cymbal-adb-data`**.
   + Exports the container's mTLS wallet into **`.envs/tns`** and normalizes `tnsnames.ora` and `sqlnet.ora` for host connections to service **`myatp_low`** on TLS port **`1522`**.
   + Provisions parsing schema/user **`APP`**, enables ORDS REST access, and creates the pre-bundled **Oracle APEX 26.1.5** workspace **`COFFEE`** served by **ORDS 26.3** at `https://localhost:8443/ords/apex` (with Database Actions at `https://localhost:8443/ords/sql-developer`).

   > **Note on Container Flavors:** `adb-free:latest-26ai` is the default container for `make start-infra`. Setting `ORACLE_CONTAINER_FLAVOR=free` (`gvenzl/oracle-free:latest`) is reserved strictly for lightweight non-APEX runs and `make test-integration`.

2. Confirm the `cymbal-adb-free` container is running and inspect live APEX 26.1.5 + ORDS 26.3 readiness:

   ```shell
   docker ps
   make apex
   ```

   `make apex` (`uv run python manage.py infra apex status`) queries `APEX_RELEASE` over the `.envs/tns` mTLS wallet and probes `https://localhost:8443/ords/`.

3. Apply SQLSpec database migrations and load the committed demo fixtures (specialty coffee products with 3072-dimensional `gemini-embedding-2` vectors, DFW store locations, and store inventory):

   ```shell
   uv run coffee upgrade
   ```

---

## Step 7: Run the Web Application (Port `8000`) & Explore Oracle Vector Search

1. Disconnect from the current SSH session and reconnect with IAP local port forwarding so you can reach the Litestar web app (`localhost:8000`) and pre-bundled ORDS/APEX (`localhost:8443`):

   ```shell
   exit
   gcloud compute ssh --zone "$ZONE" "coffeevm" --tunnel-through-iap --project $PROJECT_ID -- \
     -L 8080:localhost:8000 \
     -L 8443:localhost:8443
   ```

   > **Tip for Local Workstation Terminals:** In Google Cloud Shell, **Web Preview** proxies HTTP port `8080`, so `-L 8080:localhost:8000` maps Web Preview directly to the Litestar app on port `8000`. If you run `gcloud compute ssh` from your own laptop terminal instead of Cloud Shell, use `-L 8000:localhost:8000 -L 8443:localhost:8443` so you can open both `http://localhost:8000` (Litestar app) and `https://localhost:8443/ords/apex` (Oracle APEX 26.1 Builder, accepting the container's self-signed TLS certificate) directly in your local browser.

2. Return to the repository directory, verify the frontend bundle, and start the Granian application server on default port `8000`:

   ```shell
   cd oracledb-vertexai-demo/
   uv run python manage.py assets build
   uv run coffee run
   ```

3. In the upper-right corner of Google Cloud Shell, click **Web Preview** -> **Preview on port 8080** (or open `http://localhost:8000` when tunneling from a local terminal) to launch the Cymbal Coffee chat interface.
4. Navigate to **`/explore`** (`http://localhost:8080/explore` via Cloud Shell Web Preview, or `http://localhost:8000/explore` locally) to open the interactive **Oracle Vector Explorer**:
   + **Simulate Raw Hybrid & Vector Queries:** Test `CTXSYS.CONTEXT` + HNSW `VECTOR(3072, FLOAT32)` matching directly without invoking a full conversational turn.
   + **Inspect Exact Query Latencies:** Compare Oracle execution timings in milliseconds across vector, full-text, and Reciprocal Rank Fusion queries.
   + **Distance & Similarity Inspection:** View calculated Cosine distance scores (`VECTOR_DISTANCE(..., COSINE) FETCH APPROX`) across matching catalog items.
   + **Analyze Oracle Execution Plans:** Inspect `DBMS_XPLAN` output verifying `VECTOR INDEX HNSW SCAN` (`INMEMORY NEIGHBOR GRAPH`) access paths.

Keep `uv run coffee run` active in this terminal (or open a second IAP SSH tab to `coffeevm`) before continuing to Steps 8 and 9.

---

## Step 8: Connect Oracle APEX 26.1 to Vertex AI (`COFFEE_VERTEX_AI`)

Oracle APEX 26.1 includes native `APEX_AI.GENERATE` PL/SQL support backed by workspace **Generative AI Services**. Cymbal Coffee supports two OpenAI-compatible connectivity paths from Oracle APEX 26.1 to Google Cloud Vertex AI (`gemini-3.8-flash`).

### Method 1 (Primary): Direct Vertex AI OpenAI-Compatible Endpoint

In direct mode, Oracle Database / APEX 26.1 calls Vertex AI's OpenAI-compatible Chat Completions endpoint over HTTPS using an OAuth2 Bearer credential stored in APEX Workspace Credentials:

+ **Base URL**: `https://aiplatform.googleapis.com/v1/projects/<VERTEX_AI_PROJECT_ID>/locations/<VERTEX_AI_LOCATION>/endpoints/openapi` (`location` defaults to `global`)
+ **AI Provider**: `OpenAI` (Generic OpenAI-compatible)
+ **Model**: `google/gemini-3.8-flash`
+ **Web Credential Static ID**: `VERTEX_AI_CRED` (HTTP Header `Authorization` = `Bearer <oauth2-access-token>`)
+ **Generative AI Service Static ID**: `COFFEE_VERTEX_AI` (`Used by App Builder = Yes`)

1. **Automated CLI Provisioning & Live `APEX_AI.GENERATE` Verification** — From a terminal inside `coffeevm` (`cd ~/oracledb-vertexai-demo`), provision the `DBMS_NETWORK_ACL_ADMIN` host ACEs for `aiplatform.googleapis.com:443`, create `VERTEX_AI_CRED` and `COFFEE_VERTEX_AI` in workspace `COFFEE`, and run a live `APEX_AI.GENERATE` verification prompt:

   ```shell
   export VERTEX_AI_PROJECT_ID=$(gcloud config get-value project)
   uv run python manage.py infra apex configure-vertex \
     --mode direct \
     --project "$VERTEX_AI_PROJECT_ID" \
     --verify
   ```

2. **Refreshing the OAuth2 Access Token (~60-Minute Expiry)** — Google Cloud OAuth2 access tokens expire after roughly 60 minutes. Refresh `VERTEX_AI_CRED` in place without recreating `DBMS_NETWORK_ACL_ADMIN` host ACEs:

   ```shell
   uv run python manage.py infra apex configure-vertex \
     --mode direct \
     --refresh-token \
     --verify
   ```

3. **Equivalent Manual APEX 26.1 Builder UI Walkthrough** — To inspect or configure the exact same objects interactively in APEX Builder:
   1. Open `https://localhost:8443/ords/apex` and sign in to **Workspace** `COFFEE` as **Username** `APP` with **Password** `SuperSecret1`.
   2. Navigate to **App Builder** -> **Workspace Utilities** -> **All Workspace Utilities** -> **Web Credentials** and select (or create) **`VERTEX_AI_CRED`**:
      + **Name**: `Vertex AI OAuth2 Bearer`
      + **Static ID**: `VERTEX_AI_CRED`
      + **Authentication Type**: `HTTP Header`
      + **Credential Name**: `Authorization`
      + **Credential Secret**: `Bearer <oauth2-access-token>` (minted via `gcloud auth print-access-token`)
   3. Navigate to **App Builder** -> **Workspace Utilities** -> **Generative AI** and select (or create) **`COFFEE_VERTEX_AI`**:
      + **AI Provider**: `OpenAI`
      + **Name**: `Cymbal Coffee Vertex AI`
      + **Static ID**: `COFFEE_VERTEX_AI`
      + **Used by App Builder**: `Yes`
      + **Base URL**: `https://aiplatform.googleapis.com/v1/projects/<VERTEX_AI_PROJECT_ID>/locations/global/endpoints/openapi`
      + **Credential**: `VERTEX_AI_CRED`
      + **Model**: `google/gemini-3.8-flash`
   4. Click **Test Connection** to verify the HTTPS handshake from APEX 26.1 to Vertex AI.

### Method 2 (Secondary / Zero-Expiry Local Dev & mTLS Workstations): Litestar OpenAI-Compatible Gateway

For local development loops where you want zero 60-minute OAuth2 token rotation — or on corporate mTLS workstations where containers cannot present host-bound mTLS device certificates directly to `aiplatform.googleapis.com` — Cymbal Coffee ships an OpenAI-compatible Vertex AI gateway on `ApexAIController` (`src/app/domain/products/controllers/_apex_ai.py`):

+ **Base URL**: `http://host.docker.internal:8000/api/apex/ai/v1`
+ **Endpoints**: `GET /api/apex/ai/v1/models` and `POST /api/apex/ai/v1/chat/completions`
+ **Model**: `gemini-3.8-flash`
+ **Optional Auth**: Set `APEX_GATEWAY_API_KEY` in `.env` to enforce constant-time Bearer token authentication between APEX (`VERTEX_AI_CRED`) and the Litestar gateway.

1. Ensure the Litestar app is running and listening on `0.0.0.0:8000` (`LITESTAR_HOST=0.0.0.0` in `.env`, or `uv run coffee run --host 0.0.0.0`) so `cymbal-adb-free` can reach `host.docker.internal:8000`.
2. Switch `COFFEE_VERTEX_AI` to gateway mode and verify a live `APEX_AI.GENERATE` round-trip:

   ```shell
   uv run python manage.py infra apex configure-vertex --mode gateway --verify
   ```

---

## Step 9: Validate, Import, and Run the Cymbal Coffee APEX 26.1 App (`App ID 100`)

The repository ships a complete **APEXlang** source definition for **Cymbal Coffee — Vertex AI & Operations** under `src/apex/cymbal-coffee-ops/` (`compatibilityMode: 26.1`, Application ID `100`), managed with Oracle SQLcl `26.1.2+`.

1. **Validate the APEXlang Source Offline**:

   ```shell
   uv run python manage.py infra apex validate --alias cymbal-coffee-ops
   ```

2. **Import Application `100` into Workspace `COFFEE` (Parsing Schema `APP`)**:

   ```shell
   uv run python manage.py infra apex import \
     --alias cymbal-coffee-ops \
     --workspace COFFEE \
     --schema APP \
     --app-id 100
   ```

3. **Walk Through the Live APEX 26.1 Pages** — Open `https://localhost:8443/ords/r/coffee/cymbal-coffee-ops/` and sign in with `APP` / `SuperSecret1`:
   + **Page 6 — Vertex AI Coffee Concierge** (`/ords/r/coffee/cymbal-coffee-ops/vector-recommendations`): Enter a tasting prompt such as *"Recommend a bright floral pour-over and a pastry pairing"* (and an optional category filter such as `Whole Bean` or `Bakery`), then click **Ask Vertex AI**. The `run-vertex-concierge` PL/SQL process queries live in-stock `PRODUCT` rows, assembles the grounded catalog context, and invokes `APEX_AI.GENERATE(p_service_static_id => 'COFFEE_VERTEX_AI')` while the **Grounded Catalog Candidates** Interactive Report displays `HNSW Ready (3072d)` status alongside each product.
   + **Page 3 — DFW Store Directory** (`/ords/r/coffee/cymbal-coffee-ops/stores`): Inspect how the Interactive Report constructs keyless Google Maps search URLs (`https://www.google.com/maps/search/?api=1&query=...`) purely from seeded `STORE` street addresses via `UTL_URL.ESCAPE`, matching `GET /api/apex/stores` without requesting, caching, logging, or persisting user browser coordinates.
   + **Page 7 — 26ai & Vertex AI Health** (`/ords/r/coffee/cymbal-coffee-ops/integration-health`): Review the live diagnostic reports querying `APEX_RELEASE` (`26.1.5`), `APEX_WORKSPACE_CREDENTIALS` (`VERTEX_AI_CRED`) alongside the `COFFEE_VERTEX_AI` Generative AI Service (`generative_ai_service_id` and `/api/apex/ai/v1` `litestar_gateway_path`), 3072-dimensional `gemini-embedding-2` vector coverage across `PRODUCT`, and Oracle 26ai AI schema metadata in `USER_ANNOTATIONS_USAGE`.

4. **Export APEX Builder Customizations Back to APEXlang Source** — After editing any page or region in APEX Builder, export deterministic APEXlang `.apx` files back into `src/apex/cymbal-coffee-ops/`:

   ```shell
   uv run python manage.py infra apex export --app-id 100 --alias cymbal-coffee-ops
   ```

---

## Advanced Challenge Tasks for Workshop Graduates

Once the core Litestar and APEX 26.1 applications are running, explore the following architectural expansion exercises.

### Challenge 1: Implement Persistent Chat Conversation Logging to Google BigQuery

**Objective:** Stream chat turns, user prompts, and response latencies into Google BigQuery for analytics and quality monitoring using SQLSpec's `BigQueryConfig`.

+ **Step A: Enable BigQuery & Create the Dataset** — Run these commands in **Google Cloud Shell** (outside the VM):

  ```shell
  gcloud services enable bigquery.googleapis.com
  bq mk --dataset --location=us-central1 coffee_analytics
  ```

+ **Step B: Create the Target Table Schema** — Run this in **Google Cloud Shell** (outside the VM):

  ```shell
  bq mk --table coffee_analytics.chat_logs \
    session_id:STRING,timestamp:TIMESTAMP,user_query:STRING,response_text:STRING,latency_ms:INTEGER
  ```

+ **Step C: Grant BigQuery IAM Permissions to the VM** — Run this in **Google Cloud Shell** (outside the VM):

  ```shell
  PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"
  ```

+ **Step D: Add the BigQuery Client Dependency** — Inside the **VM** (`coffeevm`), add `google-cloud-bigquery` to the project environment:

  ```shell
  cd ~/oracledb-vertexai-demo/
  uv add google-cloud-bigquery
  ```

+ **Step E: Extend the Chat Controller Layer (Full File Drop-in Replacement)** — Open `src/app/domain/chat/controllers/_chat.py` and replace its contents with the following controller, which logs completed chat turns asynchronously via SQLSpec's `BigQueryConfig`:

  ```py
  """Coffee chat controller for streaming agent conversations and session resets."""

  import re
  import time
  from collections.abc import AsyncIterator
  from datetime import UTC, datetime
  from typing import Any, ClassVar

  import structlog
  from litestar import post
  from litestar.exceptions import ValidationException
  from litestar.response import ServerSentEvent
  from litestar_htmx import HTMXRequest
  from litestar_security import AuthenticationPolicy, PublicController, exclude
  from sqlspec.adapters.bigquery import BigQueryConfig
  from sqlspec.utils.sync_tools import async_

  from app.domain.ai.services import AgentOrchestrationService
  from app.domain.chat._session import chat_session_identity, clear_chat_session_id
  from app.domain.chat.controllers._helpers import chat_form_from_request, location_context_from_form
  from app.lib.di import Inject
  from app.lib.exceptions import AIServiceUnconfigured, is_credential_error, is_expected_service_unavailable
  from app.utils.serialization import encode_json

  __all__ = ("CoffeeChatController",)

  logger = structlog.get_logger()
  _STREAM_ERROR_MESSAGE = "Chat failed while streaming. Please try again."
  _UNCONFIGURED_STREAM_MESSAGE = "Vertex AI service is not configured."


  class CoffeeChatController(PublicController):
      """Coffee chat API controller — JSON for SPA clients, HTML partials for HTMX."""

      auth: ClassVar[AuthenticationPolicy] = exclude()

      @staticmethod
      def validate_message(message: str) -> str:
          """Validate and sanitize user message input.

          Args:
              message: Raw user input text.

          Returns:
              The cleaned and bounded message string.

          Raises:
              ValidationException: If the sanitized message is empty.
          """
          message = re.sub(r"<[^>]+>", "", message)
          max_length = 500
          if len(message) > max_length:
              message = message[:max_length]
          message = message.replace("\x00", "").strip()

          if not message:
              raise ValidationException(detail="Message cannot be empty")

          return message

      @staticmethod
      def validate_persona(persona: str) -> str:
          """Validate persona input.

          Args:
              persona: Requested barista persona identifier.

          Returns:
              The validated persona or the default barista persona.
          """
          if persona not in {"barista", "snob", "scientist", "wellness"}:
              return "barista"
          return persona

      @post(path="/api/chat/stream", name="chat.api.stream", opt={"exclude_from_csrf": False})
      async def stream_chat_message(
          self, orchestrator: Inject[AgentOrchestrationService], request: HTMXRequest
      ) -> ServerSentEvent:
          """Stream chat response events for the browser chat UI.

          Args:
              orchestrator: Injected agent orchestration service.
              request: Active HTMX request with form data and session context.

          Returns:
              ServerSentEvent instance streaming JSON event frames.
          """
          data = await chat_form_from_request(request)
          clean_message = self.validate_message(data.message)
          validated_persona = self.validate_persona(data.persona)
          location_context = location_context_from_form(data)
          user_id, session_id = chat_session_identity(request)

          async def stream_events() -> AsyncIterator[dict[str, str]]:
              start_time = time.time()
              final_payload: dict[str, Any] = {}

              try:
                  async for frame in orchestrator.stream_conversation_turn(
                      session_id=session_id,
                      user_id=user_id,
                      message=clean_message,
                      services=request,
                      persona=validated_persona,
                      location_context=location_context,
                  ):
                      if frame.get("type") == "final":
                          final_payload = frame

                      frame_type = str(frame.get("type", "message"))
                      yield {"event": frame_type, "data": encode_json(frame)}

                  if final_payload:
                      await self._log_turn_to_bigquery(
                          session_id=session_id,
                          user_query=clean_message,
                          response_text=str(final_payload.get("answer", "")),
                          start_time=start_time,
                      )

              except Exception as exc:
                  if is_credential_error(exc) or is_expected_service_unavailable(exc):
                      detail = (
                          exc.detail
                          if isinstance(exc, AIServiceUnconfigured) and exc.detail
                          else _UNCONFIGURED_STREAM_MESSAGE
                      )
                      await logger.awarning(
                          "Chat stream unavailable due to AI configuration", error_type=type(exc).__name__, detail=detail
                      )
                      yield {"event": "error", "data": encode_json({"type": "error", "message": detail})}
                  else:
                      await logger.aexception(
                          "Chat stream failed after response started", error_type=type(exc).__name__, detail=str(exc)
                      )
                      yield {"event": "error", "data": encode_json({"type": "error", "message": _STREAM_ERROR_MESSAGE})}

          return ServerSentEvent(stream_events(), status_code=200)

      @post(
          path="/api/chat/session/clear", name="chat.api.clear_session", status_code=200, opt={"exclude_from_csrf": False}
      )
      async def clear_chat_session(
          self, orchestrator: Inject[AgentOrchestrationService], request: HTMXRequest
      ) -> dict[str, str]:
          """Clear the anonymous browser's agent chat session.

          Args:
              orchestrator: Injected agent orchestration service.
              request: Active HTMX request.

          Returns:
              JSON confirmation response.
          """
          user_id, session_id = chat_session_identity(request)
          await orchestrator.clear_session(session_id=session_id, user_id=user_id)
          clear_chat_session_id(request)
          return {"status": "cleared"}

      @staticmethod
      async def _log_turn_to_bigquery(*, session_id: str, user_query: str, response_text: str, start_time: float) -> None:
          """Persist one completed chat turn row to BigQuery asynchronously.

          Args:
              session_id: Anonymous chat session identifier.
              user_query: Sanitized user prompt text.
              response_text: Final assistant answer text.
              start_time: Epoch timestamp when streaming began.
          """
          row = {
              "session_id": session_id,
              "timestamp": datetime.now(UTC).isoformat(),
              "user_query": user_query,
              "response_text": response_text,
              "latency_ms": int((time.time() - start_time) * 1000),
          }

          def write_row() -> None:
              config = BigQueryConfig()
              with config.provide_session() as driver:
                  driver.load_from_records("coffee_analytics.chat_logs", [row])

          try:
              await async_(write_row)()
          except Exception as exc:
              await logger.awarning("BigQuery logging failed", error=str(exc))
  ```

  > **Note:** SQLSpec's `BigQueryConfig` and `load_from_records` run off the event loop via `async_` (`sqlspec.utils.sync_tools`), so streaming SSE chat frames are never blocked by analytics writes and raw user browser coordinates are never logged.

  Restart the server and send a chat message to verify rows appear in `coffee_analytics.chat_logs`:

  ```shell
  uv run coffee run
  ```

---

### Challenge 2: Embed Interactive Google Maps Iframes for Store Cards

**Objective:** Render an opt-in Google Maps Embed iframe inside store cards using seeded `STORE` coordinates while keeping keyless Google Maps links active by default.

+ **Step A: Provision a Restricted Maps Embed API Key**
  1. In the Google Cloud Console, open **Google Maps Platform** -> **Overview** and complete the one-time API initialization if prompted.
  2. Navigate to **Keys & Credentials** -> **Create Credentials** -> **API Key**.
  3. Click **Restrict Key** and under **API Restrictions** select **Maps Embed API** (never reuse a Gemini or Vertex key for browser embeds).

+ **Step B: Configure `.env`** — Add the Maps Embed variables to `.env` inside `coffeevm`:

  ```ini
  MAPS_ENABLE_EMBED=true
  GOOGLE_MAPS_EMBED_API_KEY=your_newly_created_restricted_key_here
  ```

+ **Step C: Expose `Settings.from_env()` to the Page Templates**
  1. Open `src/app/domain/web/controllers/_pages.py` and replace its contents with the following updated controller so both `chat_page` and `explore_page` pass `settings` alongside the explore telemetry context:

     ```py
     """Page-level routes for the HTMX frontend."""

     from typing import Annotated

     import structlog
     from litestar import get
     from litestar.params import QueryParameter
     from litestar.response import Template
     from litestar_htmx import HTMXRequest
     from litestar_security import PublicController

     from app.domain.ai.services import AgentOrchestrationService
     from app.domain.chat import chat_session_identity
     from app.domain.products.services import StoreService, build_explore_telemetry_context
     from app.lib.di import Inject
     from app.lib.settings import Settings

     __all__ = ("PageController",)

     logger = structlog.get_logger()


     class PageController(PublicController):
         """Server-rendered page routes for chat and explore."""

         @get(path="/", name="pages.chat", include_in_schema=False)
         async def chat_page(self, request: HTMXRequest, orchestrator: Inject[AgentOrchestrationService]) -> Template:
             """Render the primary coffee chat landing page with session history.

             Args:
                 request: Active HTMX request.
                 orchestrator: Injected agent orchestration service.

             Returns:
                 Rendered Jinja template for chat page.
             """
             user_id, session_id = chat_session_identity(request)
             try:
                 history_messages = await orchestrator.get_display_history(session_id=session_id, user_id=user_id)
             except Exception as exc:
                 await logger.awarning("Chat history retrieval failed", error_type=type(exc).__name__)
                 history_messages = []
             return Template(
                 template_name="pages/chat.html.j2",
                 context={"history_messages": history_messages, "settings": Settings.from_env()},
             )

         @get(path="/explore", name="pages.explore", include_in_schema=False)
         async def explore_page(
             self,
             stores_service: Inject[StoreService],
             search_query: Annotated[str | None, QueryParameter(name="query")] = None,
         ) -> Template:
             """Render the explore and vector search page.

             Args:
                 stores_service: Injected store service.
                 search_query: Optional search query parameter.

             Returns:
                 Rendered Jinja template for explore page.
             """
             try:
                 stores = await stores_service.get_all_stores()
             except Exception as exc:
                 await logger.awarning("Store inventory selector unavailable", error_type=type(exc).__name__)
                 stores = []
             query_value = search_query or ""
             telemetry_ctx = build_explore_telemetry_context(query_value, matches=[])
             return Template(
                 template_name="pages/explore.html.j2",
                 context={"query": query_value, "stores": stores, "settings": Settings.from_env(), **telemetry_ctx},
             )
     ```

  2. Open `src/app/domain/web/templates/base.html.j2` and update the `<body>` tag on line 19 to expose the Maps Embed attributes:

     ```html
     <body hx-ext="litestar" data-app-shell="true"
           data-maps-enabled="{{ 'true' if settings.maps.embed_enabled else 'false' }}"
           data-maps-key="{{ settings.maps.EMBED_API_KEY }}"
           class="app-shell font-sans text-strong antialiased">
     ```

+ **Step D: Render the Google Maps Embed Iframe in `src/resources/chat-stream.js`** — Open `src/resources/chat-stream.js`, locate `renderStoreCard(row, mapActions)`, and replace it with the version below:

  ```javascript
  const renderStoreCard = (row, mapActions) => {
    const { search, directions } = mapActions || {}
    const name = rowValue(row, ["store_name", "storeName", "name"], "Cymbal Coffee")
    const address = rowValue(row, ["store_address", "storeAddress", "address"])
    const locality = formatLocality(row)
    const phone = rowValue(row, ["phone", "store_phone", "storePhone"])
    const hours = formatHoursSummary(rowValue(row, ["hours"], null))
    const distance = formatDistance(rowValue(row, ["distance_miles", "distanceMiles"], null))
    const productName = rowValue(row, ["product_name", "productName"])
    const quantity = rowValue(row, ["quantity_available", "quantityAvailable"], null)
    const stockStatus = rowValue(row, ["stock_status", "stockStatus"])
    const pickupAvailable = rowValue(row, ["pickup_available", "pickupAvailable"], null)
    const stockClass =
      stockStatus === "IN_STOCK"
        ? "border-success/25 bg-success/10 text-success"
        : stockStatus === "LOW_STOCK"
          ? "border-accent/25 bg-accent-soft text-accent-strong"
          : "border-danger/25 bg-danger/10 text-danger"

    const mapsEnabled = document.body.dataset.mapsEnabled === "true"
    const mapsApiKey = document.body.dataset.mapsKey
    const lat = rowValue(row, ["latitude", "store_latitude"], null)
    const lng = rowValue(row, ["longitude", "store_longitude"], null)
    const iframeMarkup =
      mapsEnabled && mapsApiKey && lat && lng
        ? `<div class="map-container mt-3 overflow-hidden rounded-lg border border-border shadow-sm">
             <iframe
               width="100%"
               height="220"
               style="border:0"
               loading="lazy"
               allowfullscreen
               referrerpolicy="no-referrer-when-downgrade"
               src="https://www.google.com/maps/embed/v1/place?key=${encodeURIComponent(mapsApiKey)}&q=${encodeURIComponent(`${lat},${lng}`)}">
             </iframe>
           </div>`
        : ""

    return `<article class="mt-3 rounded-lg border border-border bg-surface-strong/60 p-3">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
          <h3 class="text-sm font-semibold text-strong">${escapeHtml(String(name))}</h3>
          <p class="mt-1 text-xs text-muted">${escapeHtml([address, locality].filter(Boolean).join(", "))}</p>
        </div>
        ${distance ? `<span class="telemetry-chip border-sage/25 bg-sage/10 text-sage">${escapeHtml(distance)}</span>` : ""}
      </div>
      <div class="mt-3 grid gap-2 text-xs text-muted sm:grid-cols-2">
        ${phone ? `<span>${escapeHtml(String(phone))}</span>` : ""}
        ${hours ? `<span>${escapeHtml(hours)}</span>` : ""}
        ${productName ? `<span class="font-medium text-strong">${escapeHtml(String(productName))}</span>` : ""}
        ${quantity !== null ? `<span>${escapeHtml(String(quantity))} available</span>` : ""}
      </div>

      ${iframeMarkup}

      <div class="mt-3 flex flex-wrap items-center gap-2">
        ${stockStatus ? `<span class="telemetry-chip ${stockClass}">${escapeHtml(formatStockStatus(stockStatus))}</span>` : ""}
        ${
          pickupAvailable !== null
            ? `<span class="telemetry-chip border-border bg-surface text-muted">${pickupAvailable ? "Pickup available" : "Pickup unavailable"}</span>`
            : ""
        }
        ${
          search
            ? `<a href="${escapeHtml(search.url)}" target="_blank" rel="noopener noreferrer" class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-accent-strong transition-colors hover:border-accent/40 hover:bg-accent-soft">Open in Google Maps</a>`
            : ""
        }
        ${
          directions
            ? `<a href="${escapeHtml(directions.url)}" target="_blank" rel="noopener noreferrer" class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-accent-strong transition-colors hover:border-accent/40 hover:bg-accent-soft">Get directions</a>`
            : ""
        }
      </div>
    </article>`
  }
  ```

+ **Step E: Rebuild Frontend Assets and Restart Granian**

  ```shell
  uv run python manage.py assets build
  uv run coffee run
  ```

  Ask the chat *"Where can I buy a Nitro Cold Brew?"* to see the embedded map alongside the keyless Google Maps action links.

---

## Appendix: Code Deep Dive & Key Components

### 1. SQLSpec `0.69.0` Services & Pool Isolation (`src/app/lib/service.py`, `src/app/lib/settings/_database.py`)

Cymbal Coffee uses **SQLSpec `0.69.0`** (`OracleLoaderService` and `OracleAsyncConfig`) rather than an ORM:

+ Named SQL queries live in `src/app/db/sql/*.sql` (with packaged APEX CDN deployment PL/SQL in `src/app/db/sql/deploy/configure-apex-cdn.sql` and `src/app/db/sql/deploy/revert-apex-cdn.sql`, invoked via `uv run coffee configure-apex-cdn`), while simple CRUD uses SQLSpec `sql.insert`, `sql.update`, and `sql.delete` builders.
+ Python `list[float]` values bind directly to Oracle `VECTOR(3072, FLOAT32)` columns (`gemini-embedding-2`), and LOB columns under 1 GB return inline values directly without extra locator round-trips.
+ `DatabaseSettings` enables `enable_session_tracing`, wire-level `sqlcommenter` trace context propagation, native `wallet_zip` extraction for Autonomous Database mTLS wallets, immutable `FrozenBaseStruct` DTOs, and an isolated `queue_db` pool (`DatabaseSettings.get_queue_config()`, `session_key="queue_db_session"`) for `litestar-queues`.

### 2. Dishka Dependency Injection (`src/app/ioc/`)

Database drivers, `GeminiModelClient`, domain services, and settings are resolved at handler boundaries through **Dishka** providers (`src/app/ioc/_config.py`, `_database.py`, `_ai.py`, `_domain.py`).

### 3. Native `AgentRuntime` & Oracle APEX 26.1 Gateway (`src/app/domain/ai/`, `src/app/domain/products/controllers/_apex_ai.py`)

Conversational planning, tool execution, and streaming SSE events are orchestrated by the native **`AgentRuntime`** (`app.domain.ai`) on Vertex AI **`gemini-3.8-flash`**, persisting session and event state in Oracle tables (`agent_session` and `agent_event`). `ApexAIController` exposes `/api/apex/ai/v1` so Oracle APEX 26.1 `APEX_AI.GENERATE` (`COFFEE_VERTEX_AI`) can target either Vertex AI's direct `/endpoints/openapi` endpoint or the local Litestar gateway interchangeably.
