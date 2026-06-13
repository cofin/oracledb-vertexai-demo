# Hands-on Lab: Cymbal Coffee — Oracle 26ai \+ Vertex AI AI-Powered Agent

Welcome to the **Cymbal Coffee Hands-on Lab**. In this workshop, you will step-by-step setup, configure, ingest data into, and run a premium next-generation AI-powered coffee recommendation application. For complete background concepts and documentation material, please visit the official [Cymbal Coffee Documentation Site](https://cofin.github.io/oracledb-vertexai-demo/index.html).

The application uses **Oracle Database 26ai** for semantic vector search (`VECTOR(3072, FLOAT32)` with HNSW INMEMORY indexes), **Google Cloud Vertex AI** for enterprise-grade text embeddings (`gemini-embedding-001`) and large language model orchestration (`gemini-2.5-flash-lite`), and **Google ADK 2.0** as the multi-agent planning engine. The application frontend is built on **Litestar 2**, **HTMX**, and **Jinja templates**, managed with **Dishka Dependency Injection** and served using the high-performance **Granian** ASGI server.

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

4. Define the default geographic deployment regions and zones:

```shell
export REGION=us-central1
export ZONE=us-central1-c
export PROJECT_ID=$(gcloud config get-value project)
export USER=<Your provided user e.g. devstarxxxx@gcplab.me>

gcloud config set compute/region $REGION
gcloud config set compute/zone $ZONE
```

5. Enable the necessary Google Cloud Services APIs for Compute Engine, Identity-Aware Proxy, Vertex AI, and Maps backends:

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

2. Bind the IAP tunnel resource accessor role to your cloud user account:

```shell
gcloud projects add-iam-policy-binding $PROJECT_ID \
 --member="user:$USER" \
 --role="roles/iap.tunnelResourceAccessor"
```

3. Create a Cloud Router to serve as the backbone for safe internet outbound requests (needed to download system packages and container images):

```shell
gcloud compute routers create default-router --network=default
```

4. Provision a NAT Gateway associated with the router so the VM can talk out to the internet safely without an external public IP:

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

1. Run the following command in Cloud Shell to create a `e2-standard-4` (4 vCPUs, 16 GB RAM) Ubuntu 22.04 LTS virtual machine:

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
  --create-disk=auto-delete=yes,boot=yes,device-name=coffeevm,image=projects/ubuntu-os-cloud/global/images/ubuntu-2204-jammy-v20241115,mode=rw,size=100,type=pd-balanced
```

2. Grant the attached Compute Engine default service account permissions to invoke Vertex AI models:

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

2. Once inside the VM terminal, configure the system to automatically restart background services without prompting interactive dialog screens (this avoids environment variables being stripped away by `sudo` operations):

```shell
sudo sed -i "s/#\$nrconf{restart} = 'i';/\$nrconf{restart} = 'a';/g" /etc/needrestart/needrestart.conf
```

3. Refresh the package index logs:

```shell
sudo apt update
```

4. Purge any legacy node packages to prevent library conflicts:

```shell
sudo apt purge -y nodejs npm libnode-dev
```

5. Clean up legacy dependencies:

```shell
sudo apt autoremove -y
```

6. Install core utilities, compilation dependencies, Docker, and curl:

```shell
sudo apt install -y docker.io docker-compose build-essential python3.10-venv git curl
```

7. Fetch and register the modern NodeSource Node.js v20 distribution setup:

```shell
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
```

8. Install the updated modern Node.js engine:

```shell
sudo apt install -y nodejs
```

9. Grant your local user account permission to interact with Docker without needing root sudo flags:

```shell
sudo usermod -aG docker $USER
```

10. **Crucial Step**: Type `exit` to disconnect from the VM session, then reconnect using the exact same command to apply the new group membership permissions:

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

2. Run the idempotent `make install` workflow. This script will automatically download `uv` (the lightning-fast Python toolchain manager), build frontend assets, and configure localized paths:

```shell
export PATH=$PATH:~/.local/bin
make install
```

3. Initialize your environmental variables file using the project interactive initializer:

```shell
uv run python manage.py init
```

   *Follow the prompts to match your current environment. For deployment mode select `managed`. When prompted for `VERTEX_AI_PROJECT_ID`, enter your actual GCP project ID. Keep database passwords as `super-secret` and database user as `app`.*

---

## Step 6: Startup Oracle 26ai Database and Load Fixture Vectors

1. Spin up the infrastructure layer, which downloads and runs the Oracle Database 26ai container image alongside a Valkey caching instance:

```shell
make start-infra
```

2. Verify that both container systems are active and healthy:

```shell
docker ps
```

3. Apply database migrations, construct tables, and populate the database with committed demo fixtures (122 coffee items, 16 premium store locations):

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

2. Move back to the application directory, build the frontend assets, and start the Granian dev app server:

```shell
cd oracledb-vertexai-demo/
uv run python manage.py assets build
uv run coffee run
```

3. In the upper right area of your Google Cloud Shell browser screen, click the **Web Preview** button and select **Preview on port 8080**. A new tab will open displaying the beautiful chat recommendation layout\!  
4. Visit **`http://localhost:8080/explore`** (via the same tunnel web preview) to access the interactive **Oracle Vector Explorer**. This dedicated diagnostic tool allows you to look directly under the hood of Oracle 26ai vector search operations:  
   - **Simulate Raw Vector Queries:** Input any product description or user phrase to test vector matching without running the full LLM multi-agent conversation flow.  
   - **Inspect Exact Query Latencies:** Review exact execution times in milliseconds to observe the high performance of modern enterprise databases processing multi-dimensional vector queries.  
   - **Distance Comparison Strategies:** Visualize calculated vector distance scores (e.g., Cosine or Euclidean distances) between query embeddings and product row metadata.  
   - **Analyze Oracle EXPLAIN PLANS:** Click on query lines to open the raw database `DBMS_XPLAN.DISPLAY` outputs, revealing exact vector search access paths, filter operations, row count evaluations, and HNSW INMEMORY index usage hits.

---

## Advanced Challenge Tasks for Workshop Graduates

Once the core application is up and running, challenge yourself or your participants with the following real-world architectural expansion exercises:

### Challenge 1: Implement Persistent Chat Conversation Logging to Google BigQuery

**Objective:** Stream chat logs, user questions, and vector response latencies into a centralized serverless analytics layer for business intelligence and quality monitoring.

* **Step A: Enable the Service & Prepare Dataset** Run these commands in your **Google Cloud Shell** (not inside the VM):

```shell
gcloud services enable bigquery.googleapis.com
bq mk --dataset --location=us-central1 coffee_analytics
```

* **Step B: Create the Target Schema** Run this in your **Google Cloud Shell** (not inside the VM):

```shell
bq mk --table coffee_analytics.chat_logs \
  session_id:STRING,timestamp:TIMESTAMP,user_query:STRING,response_text:STRING,latency_ms:INTEGER
```

* **Step C: Grant BigQuery IAM Permissions to the VM** Run this in your **Google Cloud Shell** (not inside the VM):

```shell
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"
```

* **Step D: Dependency Management** Now, switch to the terminal where you are connected to the **VM** (or reconnect via SSH). Move to the application directory and add the official Google Cloud BigQuery client library into the application runtime:

```shell
cd oracledb-vertexai-demo/
uv add google-cloud-bigquery
```

* **Step E: Extend the Chat Controller Layer (Full File Drop-in Replacement)** Open the streaming endpoint controller file located at `src/app/domain/chat/controllers/_chat.py`. To eliminate any risk of alignment or Python indentation hierarchy errors, select all text inside the file and replace its entire contents with this complete updated drop-in file code:

```py
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

import re
import uuid
from collections.abc import AsyncIterator

import structlog
from litestar import Controller, Response, post
from litestar.exceptions import ValidationException
from litestar.plugins.flash import flash
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
from litestar.response import ServerSentEvent
from litestar.status_codes import HTTP_503_SERVICE_UNAVAILABLE

from app.domain.chat import schemas
from app.domain.chat.controllers._helpers import chat_form_from_request, location_context_from_form, metrics_badges
from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.services import ADKRunner, AgentToolsService
from app.domain.chat.session import adk_session_identity, clear_adk_session_identity
from app.lib.di import Inject
from app.utils.serialization import to_json

logger = structlog.get_logger()
_STREAM_ERROR_MESSAGE = "Chat failed while streaming. Please try again."


class CoffeeChatController(Controller):
    """Coffee chat API controller — JSON for SPA clients, HTML partials for HTMX."""

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

    @post(path="/api/chat", name="chat.api.send")
    async def send_chat_message(
        self,
        adk_runner: Inject[ADKRunner],
        tools_service: Inject[AgentToolsService],
        request: HTMXRequest,
    ) -> Response:
        """Handle chat submission. HTMX clients get partial HTML; SPA clients get JSON."""
        data = await chat_form_from_request(request)
        try:
            clean_message = self.validate_message(data.message)
            location_context = location_context_from_form(data)
        except ValidationException as exc:
            if request.htmx:
                return HTMXTemplate(
                    template_name="partials/chat_error.html.j2",
                    context={"error": str(exc.detail)},
                    re_target="#chat-error",
                    re_swap="innerHTML",
                )
            raise

        validated_persona = self.validate_persona(data.persona)
        user_id, session_id = adk_session_identity(request)

        try:
            result = await adk_runner.process_request(
                query=clean_message,
                user_id=user_id,
                session_id=session_id,
                persona=validated_persona,
                tools_service=tools_service,
                location_context=location_context,
            )
        except AIServiceUnconfigured as exc:
            await logger.awarning("AI service not configured", detail=exc.detail)
            if request.htmx:
                return HTMXTemplate(
                    template_name="partials/chat_error.html.j2",
                    context={"error": exc.detail},
                    re_target="#chat-error",
                    re_swap="innerHTML",
                )
            return Response(
                content={
                    "status": HTTP_503_SERVICE_UNAVAILABLE,
                    "title": exc.detail,
                    "detail": "Service Unavailable",
                },
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
            )

        answer = result.get("answer", "")
        intent = result.get("intent_detected", "GENERAL_CONVERSATION")
        from_cache = bool(result.get("from_cache", False))

        if request.htmx:
            badges = metrics_badges(result, intent, from_cache)
            latency = badges["total_ms"]
            flash(
                request,
                f"Reply in {latency} ms" + (" (cache hit)" if from_cache else ""),
                "success" if from_cache else "info",
            )
            return HTMXTemplate(
                template_name="partials/_chat_response.html.j2",
                context={
                    "message": schemas.ChatMessage(message=answer, source="ai"),
                    "intent_detected": intent,
                    "latency_ms": latency,
                    "from_cache": from_cache,
                    "embedding_cache_hit": bool(result.get("embedding_cache_hit", False)),
                    "metrics_badges": badges,
                },
                trigger_event="chat:reply-rendered",
                after="swap",
            )

        return Response(
            content=schemas.CoffeeChatReply(
                message=clean_message,
                messages=[
                    schemas.ChatMessage(message=clean_message, source="human"),
                    schemas.ChatMessage(message=answer, source="ai"),
                ],
                answer=answer,
                query_id=str(uuid.uuid4()),
                search_metrics=result.get("search_metrics", {}),
                sql_phases=result.get("sql_phases", []),
                from_cache=from_cache,
                embedding_cache_hit=bool(result.get("embedding_cache_hit", False)),
                intent_detected=intent,
                store_results=result.get("store_results", []),
                inventory_results=result.get("inventory_results", []),
                map_actions=result.get("map_actions", []),
                location_context=result.get("location_context", {}),
            ),
        )

    @post(path="/api/chat/stream", name="chat.api.stream")
    async def stream_chat_message(
        self,
        adk_runner: Inject[ADKRunner],
        tools_service: Inject[AgentToolsService],
        request: HTMXRequest,
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
            import asyncio
            from datetime import datetime, timezone
            from google.cloud import bigquery

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
                    duration_ms = int((time.time() - start_time) * 1000)
                    final_text = final_payload.get("answer", "")

                    def log_to_bigquery():
                        try:
                            client = bigquery.Client()
                            row = [{
                                "session_id": session_id,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "user_query": clean_message,
                                "response_text": final_text,
                                "latency_ms": duration_ms
                            }]
                            client.insert_rows_json("coffee_analytics.chat_logs", row)
                        except Exception as e:
                            print(f"BigQuery logging failed: {e}")

                    asyncio.get_running_loop().run_in_executor(None, log_to_bigquery)

            except Exception as exc:  # noqa: BLE001
                await logger.aexception(
                    "Chat stream failed after response started",
                    error_type=type(exc).__name__,
                    detail=str(exc),
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

---

### Challenge 2: Embed Interactive Google Maps Iframes for Store Proximity

**Objective:** Enrich the frontend UI by embedding a dynamic visual map whenever a customer asks for location details or nearby physical stores.

* **Step A: Provision a Restricted Maps API Key** Da wir das erste Mal Google Maps in diesem Cloud-Projekt verwenden, verlangt Google vor der Schlüsselerstellung eine einmalige interaktive Initialisierung des Maps-Arbeitsbereichs im Browser, um die Verbindung mit dem Rechnungskonto abzuschließen:  
    
  1. Klicke auf der angezeigten **Google Maps Platform / Overview** Willkommensseite direkt auf den großen blauen Button **"Enable APIs"**. Dadurch schließt Google die Onboarding-Einrichtung ab und schaltet das linke Menü vollständig frei.  
  2. Navigiere anschließend in der linken Leiste (oder unter **APIs & Services**) zu **Keys & Credentials** (bzw. **Credentials**).  
  3. Klicke oben auf **Create Credentials** \-\> **API Key**.  
  4. *Best Practice:* Klicke im Pop-up auf **Restrict Key** und wähle unter *API Restrictions* im Dropdown exakt die **Maps Embed API** aus, um den Schlüssel sicher abzuriegeln.


* **Step B: Configuration Setup** Open your `.env` file inside the VM and wire up the specialized configuration keys to let the backend framework detect the key:

```
MAPS_ENABLE_EMBED=true
GOOGLE_MAPS_EMBED_API_KEY=your_newly_created_restricted_key_here
```

* **Step C: Expose Settings to the Template Context & Frontend DOM (Full File Drop-in Replacement)** By default, the application template renderer doesn't inject backend config settings globally. You must pass them into the context via the page controller route.  
    
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
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate

from app.domain.chat.services import ADKRunner
from app.domain.chat.session import adk_session_identity
from app.lib.di import Inject

logger = structlog.get_logger()


class PageController(Controller):
    """Server-rendered page routes for chat and explore."""

    @get(path="/", name="pages.chat", exclude_from_auth=True, include_in_schema=False)
    async def chat_page(self, request: HTMXRequest, adk_runner: Inject[ADKRunner]) -> HTMXTemplate:
        from app.lib.settings import get_settings
        user_id, session_id = adk_session_identity(request)
        history_messages = await adk_runner.get_history_or_empty(user_id=user_id, session_id=session_id)
        return HTMXTemplate(
            template_name="pages/chat.html.j2", 
            context={"history_messages": history_messages, "settings": get_settings()}
        )

    @get(path="/explore", name="pages.explore", exclude_from_auth=True, include_in_schema=False)
    async def explore_page(self, q: str | None = None) -> HTMXTemplate:
        return HTMXTemplate(template_name="pages/explore.html.j2", context={"query": q or ""})
```

  2. Now that `settings` is available in Jinja, pass it down to the client-side JavaScript runtime. Open `src/app/domain/web/templates/base.html.j2` and locate the `<body>` tag (line 19). Add the dataset variables:

```html
<body hx-ext="litestar" data-app-shell="true" 
      data-maps-enabled="{{ 'true' if settings.maps.embed_enabled else 'false' }}"
      data-maps-key="{{ settings.maps.EMBED_API_KEY }}"
      class="app-shell font-sans text-strong antialiased">
```

* **Step D: Inject the Google Maps Iframe in the JavaScript Card Template** Open the frontend source file located at **`src/resources/main.js`**. Locate the `renderStoreCard(row, action)` function (around line 713).  
    
  Modify the function return statement string to query the body datasets and append the Google Maps Embed iframe container at the bottom of the store card:

```javascript
const renderStoreCard = (row, action) => {
  // ... existing store card variables (name, address, distance, etc.) ...

  const mapsEnabled = document.body.dataset.mapsEnabled === "true"
  const mapsApiKey = document.body.dataset.mapsKey
  const lat = rowValue(row, ["latitude", "store_latitude"])
  const lng = rowValue(row, ["longitude", "store_longitude"])

  const iframeMarkup = (mapsEnabled && mapsApiKey && lat && lng) 
    ? `<div class="map-container mt-3 rounded-lg overflow-hidden shadow-sm border border-border">
         <iframe
           width="100%"
           height="220"
           style="border:0"
           loading="lazy"
           allowfullscreen
           referrerpolicy="no-referrer-when-downgrade"
           src="https://www.google.com/maps/embed/v1/place?key=${mapsApiKey}&q=${lat},${lng}">
         </iframe>
       </div>`
    : "";

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
      ${pickupAvailable !== null ? `<span class="telemetry-chip border-border bg-surface text-muted">${pickupAvailable ? "Pickup available" : "Pickup unavailable"}</span>` : ""}
      ${action ? `<a href="${escapeHtml(action.url)}" target="_blank" rel="noopener noreferrer" class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-accent-strong transition-colors hover:border-accent/40 hover:bg-accent-soft">Open in Google Maps</a>` : ""}
    </div>
  </article>`
}
```

* **Step E: Rebuild Assets and Refresh App Server** Since you modified a frontend source asset file (`main.js`), you **must** compile it so that Vite builds the final production script bundle:

```shell
uv run python manage.py assets build
```

  Restart the server if it isn't already running (`uv run coffee run`), and ask the chat *"Where can I buy a Nitro Cold Brew?"* to see the map dynamically appear\!

---

## Appendix: Code Deep Dive & Key Components Architecture

To help you understand the inner workings of this state-of-the-art application, let's break down the core engineering patterns:

### 1\. SQLSpec Services (`src/app/lib/service.py`)

Instead of using bulky object-relational mapping wrappers, the project uses **SQLSpec** for blazing fast async database drivers. Named SQL files reside in `src/app/db/sql/`. Vector arrays are handled natively as standard Python `list[float]` types without manual binary conversion wrappers.

### 2\. Dishka Dependency Injection (`src/app/ioc.py`)

Dependencies like database pools, LLM clients, and services are resolved automatically at the request handler argument boundary using **Dishka**. You do not need manual factory overrides or ad-hoc instantiations.

### 3\. Google ADK 2.0 Chat Engine

Conversational flow planning, prompt state persistence, and agent node fallbacks are orchestrated dynamically using the **Google ADK 2.0 Workflow/BaseNode** layer. Session history is backed directly by high-performance Oracle database tables.  
