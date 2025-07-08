# Design Document: Proposed Enhancements for the OracleDB-VertexAI Application

## 1. Introduction

This document outlines a series of proposed enhancements to the existing OracleDB-VertexAI application. The current implementation provides a robust and functional baseline, successfully integrating Oracle 23AI with Google Vertex AI using a modern Python stack. The following proposals aim to build upon this foundation by improving modularity, maintainability, performance, and developer experience, focusing on the core technologies: **Litestar**, **msgspec**, **oracledb**, and **Jinja2/HTMX**.

## 2. Analysis of Current Implementation

The application follows a service-oriented architecture with a clear separation of concerns between the web layer (Litestar), business logic (Services), and data layer (Oracle 23AI). Key characteristics of the current design include:

- **Litestar:** Serves as the high-performance async web framework for both a RESTful API and HTMX-driven UI.
- **Raw SQL in Services:** A deliberate choice for clarity, services directly execute raw `oracledb` SQL queries.
- **msgspec:** Used for high-performance data validation and serialization in API endpoints.
- **Jinja2 & HTMX:** Provide a dynamic, low-JavaScript user interface through server-side rendered partials.
- **Unified Database:** Oracle 23AI is effectively used as a multi-model database, handling relational data, vectors, JSON, and caching.

While this approach is direct and effective, we can introduce patterns that will enhance the system's scalability and ease of future development.

## 3. Proposed Enhancements

### 3.1. Data Access Layer: Introducing Repositories

The current pattern of embedding raw `oracledb` cursor management directly within service classes couples business logic with data access mechanics. This leads to repetitive boilerplate (cursor creation, `try...finally`, row-to-dict mapping) and makes services harder to unit test.

**Proposal:** Introduce a dedicated **Repository Pattern**.

- **What:** A Repository is a class dedicated to data access for a single entity (e.g., `ProductRepository`, `SessionRepository`). It encapsulates all SQL queries and `oracledb` interactions.
- **Why:**
    - **Decoupling:** Services focus purely on business logic and orchestration, delegating data persistence to repositories.
    - **DRY (Don't Repeat Yourself):** Centralizes cursor management and row mapping logic.
    - **Testability:** Allows for easily mocking the repository layer in service unit tests, avoiding the need for a live database connection.

#### Clarifying the Service and Repository Layers

This refactoring introduces a clear, layered architecture that enhances readability and maintainability. The roles of each layer become highly specialized:

- **Controllers (`app/server/controllers.py`):** The entry point for HTTP requests. Responsible for parsing incoming data, validating it with `msgspec` schemas, and invoking the appropriate service method. It knows nothing about business logic or data access.

- **Services (`app/services/`):** The core of the application's business logic. A service orchestrates operations to fulfill a use case. It may call multiple repositories or even other services (e.g., `RecommendationService` calls `ProductService`). **Crucially, services are now completely decoupled from the database.** They contain no SQL, no `oracledb` code, and operate purely on data objects (DTOs).

- **Repositories (`app/db/repositories/`):** The dedicated Data Access Layer (DAL). A repository's sole responsibility is to manage the interaction with the database for a specific data entity (e.g., `Product`). It contains all the SQL queries and the logic to map database rows to application data objects.

This separation can be visualized as follows:

**New Architecture Flow:**

```
[Controller] --> [Service] --> [Repository] --> [Database]
   (HTTP)      (Business      (SQL & Data
                 Logic)         Mapping)
```

This is a significant improvement over the previous model where the Service layer was responsible for both business logic and data access, making it less focused and harder to test. The `BaseService` class in `app/services/base.py` will be **removed**, as its `get_cursor` functionality is now consolidated within the `BaseRepository`. Services will no longer inherit from it.

#### A More Robust `row_to_model` Implementation

The initial proposal for mapping database rows to models was brittle. A robust implementation must not depend on the order of columns in a `SELECT` statement. The correct approach, inspired by the existing `app/db/utils.py`, is to dynamically build a dictionary using the column names from the database cursor and then instantiate the `msgspec` model.

**The improved logic is as follows:**

1. After executing a query, get the list of column names from `cursor.description`.
2. For each row returned by the cursor (which is a tuple), create a dictionary by zipping the column names with the row's values.
3. Instantiate the target `msgspec.Struct` using keyword arguments from this dictionary (e.g., `MyModel(**row_dict)`).

This ensures that as long as the column names in the SQL query match the field names in the `Struct`, the mapping will be correct, regardless of column order.

#### Example: From Service with Raw SQL to Service with Repository

**Before (Current Pattern in `ProductService`)**

```python
# app/services/product.py (Current)
import oracledb

class ProductService:
    def __init__(self, connection: oracledb.AsyncConnection):
        self.connection = connection

    async def get_by_id(self, product_id: int) -> dict | None:
        cursor = self.connection.cursor()
        try:
            await cursor.execute("SELECT id, name FROM product WHERE id = :id", {"id": product_id})
            row = await cursor.fetchone()
            if row:
                # Manual, order-dependent mapping
                return {"id": row[0], "name": row[1]}
            return None
        finally:
            await cursor.close()
```

**After (Proposed Refactoring)**

**Step 1: Create a Robust Base Repository**

```python
# app/db/repositories/base.py (New)
from typing import Any, Generic, TypeVar
import oracledb
from app.lib.schema import BaseStruct

T = TypeVar("T", bound=BaseStruct)

class BaseRepository(Generic[T]):
    """A generic repository providing robust row-to-model mapping."""
    def __init__(self, connection: oracledb.AsyncConnection, model: type[T]):
        self.connection = connection
        self.model = model

    async def _map_row_to_model(self, cursor: oracledb.AsyncCursor, row: tuple) -> T:
        """Dynamically maps a single database row to a msgspec model."""
        column_names = [desc[0].lower() for desc in cursor.description]
        row_dict = dict(zip(column_names, row))
        return self.model(**row_dict)

    async def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> T | None:
        """Execute a query and fetch a single model instance."""
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, params or {})
            row = await cursor.fetchone()
            if row is None:
                return None
            return await self._map_row_to_model(cursor, row)

    async def fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[T]:
        """Execute a query and fetch all model instances."""
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, params or {})
            return [await self._map_row_to_model(cursor, row) async for row in cursor]
```

**Step 2: Implement a Specific Repository**

```python
# app/db/repositories/product.py (New)
from app.schemas import ProductDTO # Assuming a ProductDTO msgspec.Struct exists
from .base import BaseRepository

class ProductRepository(BaseRepository[ProductDTO]):
    def __init__(self, connection: oracledb.AsyncConnection):
        super().__init__(connection, ProductDTO)

    async def get_by_id(self, product_id: int) -> ProductDTO | None:
        # Note: Column names (id, name, etc.) must match ProductDTO fields.
        query = "SELECT id, name, description, price FROM product WHERE id = :id"
        return await self.fetch_one(query, {"id": product_id})

    async def vector_search(self, embedding: list[float], limit: int = 5) -> list[ProductDTO]:
        query = """
            SELECT id, name, description, price
            FROM product
            WHERE VECTOR_DISTANCE(embedding, :embedding, COSINE) < 0.8
            ORDER BY VECTOR_DISTANCE(embedding, :embedding, COSINE)
            FETCH FIRST :limit ROWS ONLY
        """
        return await self.fetch_all(query, {"embedding": embedding, "limit": limit})
```

**Step 3: Refactor the Service**

```python
# app/services/product.py (Refactored)
from app.db.repositories.product import ProductRepository
from app.schemas import ProductDTO

class ProductService:
    def __init__(self, product_repo: ProductRepository):
        self.repo = product_repo

    async def find_product(self, product_id: int) -> ProductDTO | None:
        # Business logic is now clean, simple, and database-agnostic.
        return await self.repo.get_by_id(product_id)
```

### 3.2. Litestar Enhancements

#### 3.2.1. Structured Dependency Injection

The current dependency injection is functional but can be made more robust and explicit using Litestar's `Provide`.

**Proposal:** Define dependencies explicitly in the application layer.

- **What:** Use Litestar's `Provide` callable in route handlers or controllers to manage dependency lifecycles.
- **Why:**
    - **Clarity:** Makes dependencies explicit and their scope (request, app) clear.
    - **Flexibility:** Easily swap implementations for testing or different environments.
    - **Lifecycle Management:** Handles setup and teardown of resources like connection pools.

**Example: Managing DB Connections**

```python
# app/asgi.py (Proposed)
from litestar import Litestar, Request
from litestar.di import Provide
import oracledb

# Assume a connection pool is created in a config module
from app.config import db_pool

async def provide_db_connection(request: Request) -> oracledb.AsyncConnection:
    """Provides a connection from the pool per request."""
    async with db_pool.acquire() as connection:
        yield connection

async def provide_product_repository(connection: oracledb.AsyncConnection) -> ProductRepository:
    return ProductRepository(connection)

# In the Litestar app definition
app = Litestar(
    route_handlers=[...],
    dependencies={
        "db_connection": Provide(provide_db_connection, sync_to_thread=False),
        "product_repo": Provide(provide_product_repository, sync_to_thread=False),
        # ... other repositories and services
    },
)
```

#### 3.2.2. Standardized API Error Responses

**Proposal:** Implement custom exception handlers to ensure all API errors return a consistent JSON structure.

- **Why:** Provides a predictable error format for API consumers, improving their ability to handle failures gracefully.

**Example: Custom Exception Handler**

```python
# app/server/exception_handlers.py (Proposed)
from litestar import Request, Response
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from app.lib.exceptions import AppServiceException # A custom base exception

class ErrorResponse(msgspec.Struct):
    detail: str
    status_code: int

def app_service_exception_handler(request: Request, exc: AppServiceException) -> Response:
    """Handles custom application exceptions and returns a structured response."""
    return Response(
        ErrorResponse(detail=exc.detail, status_code=exc.status_code),
        status_code=exc.status_code,
    )

# In the Litestar app definition
app = Litestar(
    route_handlers=[...],
    exception_handlers={
        AppServiceException: app_service_exception_handler
    }
)
```

### 3.3. `msgspec` and Schema Enhancements

The project already leverages `msgspec` for performance. We can enhance its usage for stricter validation and type safety.

**Proposal:** Use `msgspec.Meta` for constraints and `typing.NewType` for strong type hinting.

- **Why:** Catches data validation errors at the boundary of the application, ensuring services and repositories operate on valid data. `NewType` prevents accidentally mixing up different kinds of IDs (e.g., `ProductId` vs `ShopId`).

**Example: Advanced Schema Definition**

```python
# app/schemas.py (Proposed)
import msgspec
from typing import NewType

# Stronger type hints for IDs
ProductId = NewType("ProductId", int)
ShopId = NewType("ShopId", int)

class ChatMessage(msgspec.Struct):
    # Add constraints to the message field
    message: str = msgspec.field(min_length=1, max_length=2000)
    persona: str = "enthusiast"
    user_id: str

class ProductDTO(msgspec.Struct):
    id: ProductId
    name: str
    description: str | None = None
    # Add numeric constraints
    price: float = msgspec.field(ge=0)
```

### 3.4. Jinja2 & HTMX Frontend Improvements

#### 3.4.1. Reusable Template Components with Macros

**Proposal:** Use Jinja2 macros to create reusable, parameterizable UI components.

- **Why:** Reduces duplication in HTML templates and makes the frontend code more modular and easier to maintain, similar to components in a JavaScript framework.

**Example: A Reusable Product Card Macro**

```html
<!-- templates/macros/_ui_components.html (New) -->
{% macro product_card(product) %}
<div class="bg-white p-4 rounded shadow">
  <h3 class="font-bold">{{ product.name }}</h3>
  <p class="text-sm">{{ product.description }}</p>
  <p class="text-green-600 font-bold">${{ product.price }}</p>
</div>
{% endmacro %}
```

```html
<!-- templates/partials/_vector_results.html (Refactored) -->
{% from "macros/_ui_components.html" import product_card %}

<div class="grid grid-cols-2 gap-4 mt-4">
  {% for product in products %} {{ product_card(product) }} {% endfor %}
</div>
```

#### 3.4.2. Decoupling UI Events with `hx-trigger`

**Proposal:** Use custom events and `hx-trigger` to decouple frontend components.

- **Why:** Instead of one component directly targeting another (`hx-target`), it can emit a generic event that other components can listen for. This creates a more flexible and maintainable frontend architecture.

**Example: Broadcasting a "newMessage" Event**

```html
<!-- templates/coffee_chat.html (Refactored) -->

<!-- The form no longer targets a specific element. -->
<!-- Instead, it triggers a swap on the body after a successful POST. -->
<form
  hx-post="/coffee/chat/send"
  hx-swap="none"
  _="on htmx:afterOnLoad from this
         tell the body
         trigger newMessage from me"
>
  <input name="message" placeholder="Ask about coffee..." />
  <button type="submit">Send ☕</button>
</form>

<!-- The chat history now listens for the 'newMessage' event -->
<div
  id="chat-history"
  hx-get="/coffee/chat/history"
  hx-trigger="load, newMessage from:body"
  hx-swap="innerHTML"
>
  <!-- Chat history will be loaded here on page load and on new messages -->
</div>
```

### 3.5. Improving Intent Detection

The current intent detection relies on vector similarity against a static list of exemplar phrases. This is fast but can be brittle. We can improve this using more advanced Gemini capabilities.

#### Proposal 1: Hybrid Intent Detection (Low Effort, High Impact)

Continue using the fast vector search as the primary method, but add an LLM fallback for ambiguous cases.

- **Logic:**
  1. Perform vector search as usual.
  2. If the confidence score is high (e.g., > 0.80), trust the result.
  3. If the score is low (e.g., < 0.65), default to a safe option like `GENERAL_CONVERSATION`.
  4. If the score is in an "ambiguous" middle range, make a second call to the Gemini model with a **few-shot prompt** to get a more nuanced classification. This prompt includes a handful of examples to guide the model's decision.

- **Benefit:** Improves accuracy for edge cases and non-standard phrasing without the overhead of a fully fine-tuned model.

#### Proposal 2: Fine-Tuned Intent Model (High Effort, Maximum Accuracy)

For the most robust and accurate solution, fine-tune a Gemini model specifically for this classification task.

- **Logic:**
  1. **Create a Dataset:** Compile a large JSONL file containing hundreds or thousands of labeled examples (`{"text_input": "some user query", "output": "PRODUCT_RAG"}`).
  2. **Tune Model:** Use the Gemini API or Google Cloud console to train a new, specialized model on this dataset.
  3. **Simplify Router:** The `IntentRouter` becomes much simpler. It no longer performs a vector search. Instead, it makes a single, direct API call to the fine-tuned model endpoint to get the intent.

- **Benefit:** This is the production-grade standard. It yields the highest accuracy, is optimized for the specific task, and can be faster and more cost-effective per-query at scale than the hybrid approach.

## 4. Conclusion & Refactoring Benefits

The proposed enhancements build upon the solid foundation of the existing application. By introducing these patterns, we can achieve the following benefits:

- **Code Consolidation and Boilerplate Removal:** The primary benefit of this refactoring is the removal of repetitive code.
    - **Backend:** The Repository Pattern will eliminate raw `oracledb` cursor and connection management from all service classes. This boilerplate logic will be consolidated into a single `BaseRepository`, making services cleaner and more focused on business logic. The `app/services/base.py` file will be removed entirely. The `OracleVectorSearchService` in `app/services/vertex_ai.py` will also be removed, with its logic consolidated into the `ProductRepository`.
    - **Frontend:** Jinja2 macros will remove duplicated HTML blocks from templates. UI components like product cards will be defined once and reused, simplifying template maintenance.
- **Increased Maintainability:** With less duplicated code and clearer separation of concerns, the application becomes easier to understand, modify, and extend.
- **Improved Testability:** Decoupling the service layer from the data access layer allows for simpler, more reliable unit tests using mock repositories.
- **Enhanced Developer Experience:** Clearer patterns and less boilerplate lead to a faster and more enjoyable development process.
- **Greater Scalability:** The architecture is better prepared for future growth in complexity and features.

These changes represent an evolutionary step for the codebase, aligning it with best practices for building large-scale, production-ready web applications.

## 5. Implementation Plan

This section outlines the step-by-step file modifications required to implement the proposed enhancements.

### Milestone 0: Pre-Refactoring Fixes and Enhancements

This milestone addresses critical bugs and adds quality-of-life features to stabilize the current implementation before we begin the larger architectural refactor.

1. **Implement True Session Persistence:**
   - **File:** `app/server/controllers.py`, `app/services/recommendation.py`
   - **Action:**
     - Modify the `handle_coffee_chat` controller. When a new session is created by the `RecommendationService`, capture the `session_id` from the return value.
     - Set a secure, `HttpOnly` cookie on the `HTMXTemplate` response containing the `session_id`.
     - On subsequent requests, the controller will read the `session_id` from the request cookie and pass it to the `RecommendationService`. This will correctly retrieve the existing session and its chat history.

2. **Refactor Caching and Metrics Logic:**
   - **File:** `app/services/recommendation.py`
   - **Action:**
     - Refactor the `get_recommendation` method to fetch the query embedding **only once**.
     - This single embedding vector will then be passed as an argument to both the `intent_router` and the `vector_search_service`, eliminating the redundant API call.
     - Correct the metrics logging to use the _actual_ similarity score returned from the vector search, not a hardcoded value.

3. **Add `reset-embeddings` CLI Command:**
   - **File:** `app/cli.py`, `app/server/core.py`
   - **Action:**
     - Create a new Click command function named `reset_embeddings` in `app/cli.py`.
     - This function will execute the SQL `UPDATE product SET embedding = NULL, embedding_generated_on = NULL;`.
     - It will include a `--force` flag to bypass a confirmation prompt, for safety.
     - Register the new `reset_embeddings` command in `app/server/core.py` so it's available via the application's CLI.

### Milestone 1: Refactor to Repository Pattern

1. **Create Directory Structure:**
   - Create new directory: `app/db/repositories/`
   - Create new file: `app/db/repositories/__init__.py`
2. **Implement Base Repository:**
   - Create new file: `app/db/repositories/base.py` containing the generic `BaseRepository` class to handle common database operations and model mapping.
3. **Create Concrete Repositories:**
   - For each data entity, create a dedicated repository file in `app/db/repositories/`. For example:
     - `product.py`
     - `shop.py`
     - `intent_exemplar.py`
     - `user_session.py`
     - ...and so on for all other data-accessing services.
4. **Refactor Service Layer:**
   - Modify each service in `app/services/` to remove raw `oracledb` logic and inheritance from `BaseService`.
   - Instead of a database connection, change the constructor to inject the corresponding repository.
   - Delegate all data access calls to the repository methods. For example, `app/services/product.py` will be updated to use `ProductRepository`.
   - Refactor `app/services/vertex_ai.py` to remove the `OracleVectorSearchService` class.
5. **Remove Obsolete Base Service:**
   - Delete the file `app/services/base.py`.

### Milestone 2: Enhance Litestar Configuration

1. **Implement Structured Dependency Injection:**
   - Modify `app/asgi.py`.
   - Create provider functions for the database connection pool and for each new repository and service.
   - Update the `Litestar` application constructor to use a `dependencies` dictionary populated with `Provide` calls for the entire application stack (repositories injected into services).
2. **Standardize API Error Handling:**
   - Create new file: `app/lib/exceptions.py` to define a custom `AppServiceException`.
   - Modify `app/server/exception_handlers.py` to add a handler for `AppServiceException` that returns a structured JSON error response.
   - Update `app/asgi.py` to register this new exception handler in the `Litestar` app.

### Milestone 3: Improve Schema Definitions

1. **Strengthen Type Safety and Validation:**
   - Modify `app/schemas.py`.
   - Use `typing.NewType` to create distinct types for different entity IDs (e.g., `ProductId`, `ShopId`).
   - Update all `msgspec.Struct` definitions to use these new, more specific types.
   - Add field-level validation (`min_length`, `max_length`, numeric constraints) to the structs using `msgspec.field`.

### Milestone 4: Refactor Frontend Components

1. **Create Reusable Template Macros:**
   - Create new directory: `app/server/templates/macros/`
   - Create new file: `app/server/templates/macros/_ui_components.html`.
   - Implement a `product_card` macro and other potential reusable components within this file.
2. **Adopt Macros in Templates:**
   - Modify templates like `app/server/templates/partials/_vector_results.html` to import and use the new macros, reducing code duplication.
3. **Decouple UI with HTMX Events:**
   - Modify `app/server/templates/coffee_chat.html`.
   - Update the chat submission form to emit a custom event (e.g., `newMessage`) upon success instead of directly targeting the chat history `div`.
   - Update the chat history `div` to listen for this custom event using `hx-trigger`.

### Milestone 5: Implement MkDocs Documentation Site

1. **Add Dependencies:**
   - Update `pyproject.toml` to include `mkdocs` and `mkdocs-material` in a new `[project.optional-dependencies]` group named `docs`.
2. **Create Configuration:**
   - Create a new `mkdocs.yml` file in the project root.
   - Configure the `site_name`, `site_description`, and set the theme to `material`.
   - Enable modern Material theme features like `content.code.annotate`, `navigation.tabs`, and `search`.
3. **Define Navigation:**
   - In `mkdocs.yml`, create a `nav` section that mirrors the structure of the `docs/system/` directory, providing a logical reading order for the documentation.
4. **Review and Refine Content:**
   - Read through all markdown files in `docs/system/` and update them to reflect the new repository-based architecture.
   - Ensure all code examples are accurate and that inter-document links are correctly formatted for MkDocs.
5. **Add Build Command:**
   - Add a new script to `pyproject.toml` under `[tool.uv.scripts]` (or a `Makefile` target) named `serve-docs` that executes `mkdocs serve`.

## 6. Implementation Checklist

- [x] **Milestone 0: Pre-Refactoring Fixes and Enhancements**
    - [x] Implement true session persistence using cookies.
    - [x] Refactor `RecommendationService` to fetch embeddings only once.
    - [x] Correct metrics logging to use actual similarity scores.
    - [x] Add `reset-embeddings` CLI command.
- [x] **Milestone 1: Repository Pattern**
    - [x] Create `app/db/repositories/` directory and `__init__.py`.
    - [x] Create `app/db/repositories/base.py`.
    - [x] Create repository classes for all entities.
    - [x] Refactor all services in `app/services/` to use repositories.
    - [x] Consolidate `OracleVectorSearchService` into `ProductRepository` and remove the class.
    - [x] Delete `app/services/base.py`.
- [x] **Milestone 2: Litestar Enhancements**
    - [x] Refactor `app/asgi.py` with `Provide` for all dependencies.
    - [x] Create `app/lib/exceptions.py`.
    - [x] Add custom exception handler to `app/server/exception_handlers.py`.
    - [x] Register exception handler in `app/asgi.py`.
- [x] **Milestone 3: `msgspec` and Schema Enhancements**
    - [x] Update `app/schemas.py` with `NewType` for IDs.
    - [x] Update `app/schemas.py` with `msgspec.field` validation.
- [x] **Milestone 4: Jinja2 & HTMX Frontend Improvements**
    - [x] Create `app/server/templates/macros/` directory.
    - [x] Create `app/server/templates/macros/_ui_components.html` with macros.
    - [x] Refactor templates to use the new macros.
    - [x] Refactor chat interface in `coffee_chat.html` to use `hx-trigger` events.
- [ ] **Milestone 5: MkDocs Documentation Site**
    - [ ] Add `mkdocs` and `mkdocs-material` to `pyproject.toml`.
    - [ ] Create and configure `mkdocs.yml`.
    - [ ] Define the site navigation structure in `mkdocs.yml`.
    - [ ] Review and update all documentation content in `docs/system/`.
    - [ ] Add a `serve-docs` script for local development.
- [ ] **Milestone 6: Improve Intent Detection**
    - [ ] Implement Hybrid Intent Detection (Few-Shot Prompting) in `IntentRouter`.
    - [ ] (Optional) Prepare dataset and document the process for fine-tuning an intent model.
