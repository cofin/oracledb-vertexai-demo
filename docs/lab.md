# Hands-on Lab: Cymbal Coffee — Oracle 26ai \+ Vertex AI AI-Powered Agent

Welcome to the **Cymbal Coffee Hands-on Lab**. In this workshop, you will step-by-step setup, configure, ingest data into, and run a premium next-generation AI-powered coffee recommendation application. For complete background concepts and documentation material, please visit the official [Cymbal Coffee Documentation Site](https://cofin.github.io/oracledb-vertexai-demo/index.html).

The application uses **Oracle Database 26ai** for semantic vector search (`VECTOR(3072, FLOAT32)` with HNSW INMEMORY indexes), **Google Cloud Vertex AI** for enterprise-grade text embeddings (`gemini-embedding-2`) and large language model orchestration (`gemini-3.1-flash-lite`), and **Google ADK 2.0** as the multi-agent planning engine. The application frontend is built on [**Litestar 2**](https://docs.litestar.dev/), [**HTMX**](https://htmx.org/), and [**Jinja templates**](https://jinja.palletsprojects.com/), managed with [**Dishka Dependency Injection**](https://dishka.readthedocs.io/) and served using the high-performance [**Granian**](https://github.com/emmett-framework/granian) ASGI server via the [`litestar-granian`](https://github.com/cofin/litestar-granian) plugin.

---

## Prerequisites & Audience Expectations

- **GCP Knowledge**: None\! This lab is designed to be fully beginner-friendly for Google Cloud Platform.
- **Tools Required**: A web browser and access to a Google Cloud Console account with billing or credits enabled.

---

## Step 1: Google Cloud Platform Environment Setup

In this first step, you will initialize your cloud workspace and enable the necessary APIs for machine learning, maps, and virtual machines.

1. Log into the **Google Cloud Console** (`https://console.cloud.google.com`) using your workshop credentials.
2. In the top navigation bar, click the **Activate Cloud Shell** icon (a small terminal icon `>_`). Wait a few moments for the persistent Linux terminal environment to provision and connect.
3. Set your current active project using the following command (replace `[YOUR-PROJECT-ID]` with your actual GCP project ID shown on your console dashboard):

```shell
gcloud config set project [YOUR-PROJECT-ID]
```

1. Define the default geographic deployment regions and zones:

```shell
export REGION=us-central1
export ZONE=us-central1-c
export PROJECT_ID=$(gcloud config get-value project)
export USER=<Your provided user e.g. devstarxxxx@gcplab.me>

gcloud config set compute/region $REGION
gcloud config set compute/zone $ZONE
```

1. Enable the necessary Google Cloud Services APIs for Compute Engine, Identity-Aware Proxy, Vertex AI, and Maps backends:

```shell
gcloud services enable compute.googleapis.com \
                       iap.googleapis.com \
                       aiplatform.googleapis.com \
                       maps-backend.googleapis.com \
                       osconfig.googleapis.com
```

---

## Step 2: Networking and Security Configuration

To keep your virtual machine secure while allowing access, you will leverage Identity-Aware Proxy (IAP) for secure SSH tunnels without exposing public IP addresses to the open internet.

1. Create a firewall rule allowing incoming SSH traffic from the Google IAP secure proxy block:

```shell
gcloud compute firewall-rules create allow-ssh-ingress-from-iap \
 --network=default \
 --direction=INGRESS \
 --action=allow \
 --rules=tcp:22 \
 --source-ranges=35.235.240.0/20
```

1. Bind the IAP tunnel resource accessor role to your cloud user account:

```shell
gcloud projects add-iam-policy-binding $PROJECT_ID \
 --member="user:$USER" \
 --role="roles/iap.tunnelResourceAccessor"
```

1. Create a Cloud Router to serve as the backbone for safe internet outbound requests (needed to download system packages and container images):

```shell
gcloud compute routers create default-router --network=default
```

1. Provision a NAT Gateway associated with the router so the VM can talk out to the internet safely without an external public IP:

```shell
gcloud compute routers nats create default-nat-gw \
 --router=default-router \
 --auto-allocate-nat-external-ips \
 --nat-all-subnet-ip-ranges \
 --enable-logging
```

---

## Step 3: Compute Engine Virtual Machine Provisioning

Now, you will spin up a high-performance Compute Engine virtual machine where the Oracle 26ai database container and the Litestar web application will co-exist.

1. Run the following command in Cloud Shell to create a `e2-standard-4` (4 vCPUs, 16 GB RAM) Ubuntu 26.04 LTS virtual machine:

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

1. Grant the attached Compute Engine default service account permissions to invoke Vertex AI models:

```shell
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

---

## Step 4: Connect to the VM and Install Core OS Packages

Now that the virtual machine is running, you will establish a secure tunnel into it and install core tools like Docker, Git, and Python runtimes.

1. Establish a secure SSH session into the newly provisioned VM via the IAP secure tunnel:

```shell
gcloud compute ssh --zone "$ZONE" "coffeevm" --tunnel-through-iap --project $PROJECT_ID
```

1. Once inside the VM terminal, configure the system to automatically restart background services without prompting interactive dialog screens (this avoids environment variables being stripped away by `sudo` operations):

```shell
sudo sed -i "s/#\$nrconf{restart} = 'i';/\$nrconf{restart} = 'a';/g" /etc/needrestart/needrestart.conf
```

1. Refresh the package index logs:

```shell
sudo apt update
```

1. Purge any legacy node packages to prevent library conflicts:

```shell
sudo apt purge -y nodejs npm libnode-dev
```

1. Clean up legacy dependencies:

```shell
sudo apt autoremove -y
```

1. Install core utilities, compilation dependencies, Docker, and curl:

```shell
sudo apt install -y docker.io docker-compose-v2 build-essential python3.14-venv git curl
```

1. Fetch and register the modern NodeSource Node.js v24 distribution setup:

```shell
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
```

1. Install the updated modern Node.js engine:

```shell
sudo apt install -y nodejs
```

1. Grant your local user account permission to interact with Docker without needing root sudo flags:

```shell
sudo usermod -aG docker $USER
```

1. **Crucial Step**: Type `exit` to disconnect from the VM session, then reconnect using the exact same command to apply the new group membership permissions:

```shell
exit
gcloud compute ssh --zone "$ZONE" "coffeevm" --tunnel-through-iap --project $PROJECT_ID
```

---

## Step 5: Clone Repository and Configure Environment

1. Clone the official workshop repository and change into the project root directory:

```shell
git clone https://github.com/cofin/oracledb-vertexai-demo.git
cd oracledb-vertexai-demo/
```

1. Run the idempotent `make install` workflow. This script will automatically download `uv` (the lightning-fast Python toolchain manager), build frontend assets, and configure localized paths:

```shell
export PATH=$PATH:~/.local/bin
make install
```

1. Initialize your environmental variables file using the project interactive initializer:

```shell
uv run python manage.py init
```

   *Follow the prompts to match your current environment. For deployment mode select `managed`. When prompted for `VERTEX_AI_PROJECT_ID`, enter your actual GCP project ID. Keep database passwords as `SuperSecret1` and database user as `app`.*

---

## Step 6: Startup Oracle 26ai Database and Load Fixture Vectors

1. Spin up the infrastructure layer, which downloads and runs the Oracle Database 26ai container image (response and embedding caches live in Oracle tables, so no separate cache service is needed):

```shell
make start-infra
```

1. Verify that the Oracle container is active and healthy:

```shell
docker ps
```

1. Apply database migrations, construct tables, and populate the database with committed demo fixtures (130 coffee items, 17 premium store locations):

```shell
uv run coffee upgrade
```

---

## Step 7: Run the Web Application & Explore Oracle Vector Search

1. To browse the premium web interface, you need to disconnect from your current SSH session and reconnect while mapping a port forwarding tunnel:

```shell
exit
gcloud compute ssh --zone "$ZONE" "coffeevm" --tunnel-through-iap --project $PROJECT_ID -- -L8080:localhost:5006
```

1. Move back to the application directory, build the frontend assets, and start the Granian dev app server:

```shell
cd oracledb-vertexai-demo/
uv run python manage.py assets build
uv run coffee run
```

1. In the upper right area of your Google Cloud Shell browser screen, click the **Web Preview** button and select **Preview on port 8080**. A new tab will open displaying the beautiful chat recommendation layout\!
2. Visit **`http://localhost:8080/explore`** (via the same tunnel web preview) to access the interactive **Oracle Vector Explorer**. This dedicated diagnostic tool allows you to look directly under the hood of Oracle 26ai vector search operations:
   - **Simulate Raw Vector Queries:** Input any product description or user phrase to test vector matching without running the full LLM multi-agent conversation flow.
   - **Inspect Exact Query Latencies:** Review exact execution times in milliseconds to observe the high performance of modern enterprise databases processing multi-dimensional vector queries.
   - **Distance Comparison Strategies:** Visualize calculated vector distance scores (e.g., Cosine or Euclidean distances) between query embeddings and product row metadata.
   - **Analyze Oracle EXPLAIN PLANS:** Click on query lines to open the raw database `DBMS_XPLAN.DISPLAY` outputs, revealing exact vector search access paths, filter operations, row count evaluations, and HNSW INMEMORY index usage hits.

---

## Advanced Challenge Tasks for Workshop Graduates

Once the core application is up and running, challenge yourself or your participants with the following real-world architectural expansion exercises:

### Challenge 1: Implement Persistent Chat Conversation Logging to Google BigQuery

**Objective:** Stream chat logs, user questions, and vector response latencies into a centralized serverless analytics layer for business intelligence and quality monitoring.

- **Step A: Enable the Service & Prepare Dataset** Run these commands in your **Google Cloud Shell** (not inside the VM):

```shell
gcloud services enable bigquery.googleapis.com
bq mk --dataset --location=us-central1 coffee_analytics
```

- **Step B: Create the Target Schema** Run this in your **Google Cloud Shell** (not inside the VM):

```shell
bq mk --table coffee_analytics.chat_logs \
  session_id:STRING,timestamp:TIMESTAMP,user_query:STRING,response_text:STRING,latency_ms:INTEGER
```

- **Step C: Grant BigQuery IAM Permissions to the VM** Run this in your **Google Cloud Shell** (not inside the VM):

```shell
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"
```

- **Step D: Dependency Management** Now, switch to the terminal where you are connected to the **VM** (or reconnect via SSH). Move to the application directory and add the official Google Cloud BigQuery client library into the application runtime:

```shell
cd oracledb-vertexai-demo/
uv add google-cloud-bigquery
```

- **Step E: Extend the Chat Controller Layer (Full File Drop-in Replacement)** Open the streaming endpoint controller file located at `src/app/domain/chat/controllers/_chat.py`. To eliminate any risk of alignment or Python indentation hierarchy errors, select all text inside the file and replace its entire contents with this complete updated drop-in file code:

```py
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

import re
from collections.abc import AsyncIterator

import structlog
from litestar import Controller, Response, post
from litestar.exceptions import ValidationException
from litestar.plugins.htmx import HTMXRequest
from litestar.response import ServerSentEvent

from app.domain.chat.controllers._helpers import chat_form_from_request, location_context_from_form
from app.domain.chat.services import ADKRunner, AgentToolsService
from app.domain.chat.session import adk_session_identity, clear_adk_session_identity
from app.lib.di import Inject
from app.utils.serialization import to_json

logger = structlog.get_logger()
_STREAM_ERROR_MESSAGE = "Chat failed while streaming. Please try again."


class CoffeeChatController(Controller):
    """Coffee chat API controller — streaming SSE for the HTMX browser UI."""

    @staticmethod
    def validate_message(message: str) -> str:
        """Validate and sanitize user message input."""
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
        """Validate persona input."""
        if persona not in {"novice", "enthusiast", "expert", "barista"}:
            return "enthusiast"
        return persona

    @post(path="/api/chat/stream", name="chat.api.stream")
    async def stream_chat_message(
        self, adk_runner: Inject[ADKRunner], tools_service: Inject[AgentToolsService], request: HTMXRequest
    ) -> ServerSentEvent:
        """Stream chat response events for the browser chat UI."""
        data = await chat_form_from_request(request)
        clean_message = self.validate_message(data.message)
        validated_persona = self.validate_persona(data.persona)
        location_context = location_context_from_form(data)
        user_id, session_id = adk_session_identity(request)
        adk_runner.ensure_configured()

        async def stream_events() -> AsyncIterator[dict[str, str]]:
            import time
            from datetime import datetime, timezone

            from sqlspec.adapters.bigquery import BigQueryConfig
            from sqlspec.utils.sync_tools import async_

            start_time = time.time()
            final_payload = {}

            try:
                async for event in adk_runner.stream_request(
                    query=clean_message,
                    user_id=user_id,
                    session_id=session_id,
                    persona=validated_persona,
                    tools_service=tools_service,
                    location_context=location_context,
                ):
                    if event.get("type") == "final":
                        final_payload = event

                    event_type = str(event.get("type", "message"))
                    yield {"event": event_type, "data": to_json(event, as_bytes=False)}

                if final_payload:
                    row = {
                        "session_id": session_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_query": clean_message,
                        "response_text": final_payload.get("answer", ""),
                        "latency_ms": int((time.time() - start_time) * 1000),
                    }

                    def log_to_bigquery():
                        config = BigQueryConfig()
                        with config.provide_session() as driver:
                            driver.load_from_records("coffee_analytics.chat_logs", [row])

                    try:
                        await async_(log_to_bigquery)()
                    except Exception as exc:  # noqa: BLE001
                        await logger.awarning("BigQuery logging failed", error=str(exc))

            except Exception as exc:  # noqa: BLE001
                await logger.aexception(
                    "Chat stream failed after response started", error_type=type(exc).__name__, detail=str(exc)
                )
                yield {
                    "event": "error",
                    "data": to_json({"type": "error", "message": _STREAM_ERROR_MESSAGE}, as_bytes=False),
                }

        return ServerSentEvent(stream_events(), status_code=200)

    @post(path="/api/chat/session/clear", name="chat.api.clear_session", status_code=200)
    async def clear_chat_session(self, adk_runner: Inject[ADKRunner], request: HTMXRequest) -> Response:
        """Clear the anonymous browser's ADK chat session."""
        user_id, session_id = adk_session_identity(request)
        await adk_runner.clear_session(user_id=user_id, session_id=session_id)
        clear_adk_session_identity(request)
        return Response(content={"status": "cleared"})
```

> **Note:** We use SQLSpec's `BigQueryConfig` and `load_from_records` to write logs. The call is synchronous, so we wrap it with SQLSpec's `async_` (`sqlspec.utils.sync_tools`) to run it off the event loop — the chat stream is never blocked by logging, and any errors are surfaced through the app logger instead of being silently dropped.

Once you've completed your changes, start the app up and test it out.

```shell
uv run coffee run
```

---

### Challenge 2: Embed Interactive Google Maps Iframes for Store Proximity

**Objective:** Enrich the frontend UI by embedding a dynamic visual map whenever a customer asks for location details or nearby physical stores.

- **Step A: Provision a Restricted Maps API Key** Since this is the first time Google Maps is used in this Cloud project, Google requires a one-time interactive initialization of the Maps workspace in the browser — to finish linking it to your billing account — before a key can be created:

  1. On the **Google Maps Platform / Overview** welcome page that appears, click the large blue **"Enable APIs"** button. This completes the onboarding setup and unlocks the full left-hand menu.
  2. Then, in the left sidebar (or under **APIs & Services**), navigate to **Keys & Credentials** (or **Credentials**).
  3. At the top, click **Create Credentials** -> **API Key**.
  4. *Best Practice:* In the pop-up, click **Restrict Key** and, under *API Restrictions*, select exactly the **Maps Embed API** from the dropdown to lock the key down securely.

- **Step B: Configuration Setup** Open your `.env` file inside the VM and wire up the specialized configuration keys to let the backend framework detect the key:

```ini
MAPS_ENABLE_EMBED=true
GOOGLE_MAPS_EMBED_API_KEY=your_newly_created_restricted_key_here
```

- **Step C: Expose Settings to the Template Context & Frontend DOM (Full File Drop-in Replacement)** By default, the application template renderer doesn't inject backend config settings globally. You must pass them into the context via the page controller routes. Both the chat and explore pages extend the same `base.html.j2`, so both routes must provide `settings`.

  1. Open `src/app/domain/web/controllers/_pages.py`. To eliminate any risk of Python alignment or indentation errors, select all text inside the file and replace its entire contents with this complete updated drop-in file code:

```py
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Page-level routes for the HTMX frontend.

HTMX-aware partials live alongside the domain controllers that own
their data (e.g. ``app.domain.chat.controllers``,
``app.domain.products.controllers``).
"""

import structlog
from litestar import Controller, get
from litestar.params import FromQuery
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate

from app.domain.chat.services import ADKRunner
from app.domain.chat.session import adk_session_identity
from app.lib.di import Inject
from app.lib.settings import get_settings

logger = structlog.get_logger()


class PageController(Controller):
    """Server-rendered page routes for chat and explore."""

    @get(path="/", name="pages.chat", exclude_from_auth=True, include_in_schema=False)
    async def chat_page(self, request: HTMXRequest, adk_runner: Inject[ADKRunner]) -> HTMXTemplate:
        user_id, session_id = adk_session_identity(request)
        history_messages = await adk_runner.get_history_or_empty(user_id=user_id, session_id=session_id)
        return HTMXTemplate(
            template_name="pages/chat.html.j2",
            context={"history_messages": history_messages, "settings": get_settings()},
        )

    @get(path="/explore", name="pages.explore", exclude_from_auth=True, include_in_schema=False)
    async def explore_page(self, q: FromQuery[str | None] = None) -> HTMXTemplate:
        return HTMXTemplate(
            template_name="pages/explore.html.j2", context={"query": q or "", "settings": get_settings()}
        )
```

  1. Now that `settings` is available in Jinja, pass it down to the client-side JavaScript runtime. Open `src/app/domain/web/templates/base.html.j2` and locate the `<body>` tag (line 19). Add the dataset variables:

```html
<body hx-ext="litestar" data-app-shell="true"
      data-maps-enabled="{{ 'true' if settings.maps.embed_enabled else 'false' }}"
      data-maps-key="{{ settings.maps.EMBED_API_KEY }}"
      class="app-shell font-sans text-strong antialiased">
```

- **Step D: Inject the Google Maps Iframe in the JavaScript Card Template** Open the frontend source file located at **`src/resources/chat-stream.js`** (the chat UI is split into ES modules, so `renderStoreCard` lives here — not in `main.js`). Locate the `renderStoreCard(row, mapActions)` function (around line 118).

  Replace the function with this version, which reads the Maps datasets from the `<body>` element and inserts the Google Maps Embed iframe into the existing store card (the "Open in Google Maps" and "Get directions" links are preserved):

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

- **Step E: Rebuild Assets and Refresh App Server** Since you modified a frontend source asset file (`chat-stream.js`), you **must** compile it so that Vite builds the final production script bundle:

```shell
uv run python manage.py assets build
```

  Restart the server if it isn't already running (`uv run coffee run`), and ask the chat *"Where can I buy a Nitro Cold Brew?"* to see the map dynamically appear\!

---

## Appendix: Code Deep Dive & Key Components Architecture

To help you understand the inner workings of this state-of-the-art application, let's break down the core engineering patterns:

### 1. SQLSpec Services (`src/app/lib/service.py`)

Instead of using bulky object-relational mapping wrappers, the project uses **SQLSpec** for blazing fast async database drivers. Named SQL files reside in `src/app/db/sql/`. Vector arrays are handled natively as standard Python `list[float]` types without manual binary conversion wrappers.

### 2. Dishka Dependency Injection (`src/app/ioc.py`)

Dependencies like database pools, LLM clients, and services are resolved automatically at the request handler argument boundary using **Dishka**. You do not need manual factory overrides or ad-hoc instantiations.

### 3. Google ADK 2.0 Chat Engine

Conversational flow planning, prompt state persistence, and agent node fallbacks are orchestrated dynamically using the **Google ADK 2.0 Workflow/BaseNode** layer. Session history is backed directly by high-performance Oracle database tables.
