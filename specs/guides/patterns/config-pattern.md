# Configuration Pattern

## Overview

This project uses **dataclass-based settings** with environment variable fallbacks. Configuration is loaded once at startup and accessed via the `get_settings()` function throughout the application.

## Structure

```
app/lib/
├── settings.py          # All configuration classes
└── __init__.py

Configuration Hierarchy:
Settings
├── app: AppSettings
├── db: DatabaseSettings
├── server: ServerSettings
├── log: LogSettings
├── vertex_ai: VertexAISettings
├── agent: AgentSettings
└── cache: CacheSettings
```

## Settings Classes

**File**: `/home/cody/code/g/oracledb-vertexai-demo/app/lib/settings.py`

### Main Settings Container

```python
from dataclasses import dataclass, field
from functools import lru_cache

@dataclass
class Settings:
    app: AppSettings = field(default_factory=AppSettings)
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    server: ServerSettings = field(default_factory=ServerSettings)
    log: LogSettings = field(default_factory=LogSettings)
    vertex_ai: VertexAISettings = field(default_factory=VertexAISettings)
    agent: AgentSettings = field(default_factory=AgentSettings)
    cache: CacheSettings = field(default_factory=CacheSettings)

    @classmethod
    @lru_cache(maxsize=1, typed=True)
    def from_env(cls, dotenv_filename: str = ".env") -> Settings:
        """Load settings from environment (cached)."""
        env_file = Path(f"{os.curdir}/{dotenv_filename}")
        if env_file.is_file():
            from dotenv import load_dotenv
            load_dotenv(env_file, override=True)
        return Settings()

def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings.from_env()
```

### Database Settings

```python
@dataclass
class DatabaseSettings:
    """Oracle Database connection settings."""

    # Autonomous Database fields
    URL: str | None = field(default_factory=lambda: os.getenv("DATABASE_URL"))
    WALLET_PASSWORD: str | None = field(default_factory=lambda: os.getenv("WALLET_PASSWORD"))
    WALLET_LOCATION: str | None = field(
        default_factory=lambda: os.getenv("WALLET_LOCATION") or os.getenv("TNS_ADMIN")
    )

    # Standard/Local Database fields
    USER: str = field(default_factory=lambda: os.getenv("DATABASE_USER", "app"))
    PASSWORD: str = field(default_factory=lambda: os.getenv("DATABASE_PASSWORD", "super-secret"))
    HOST: str = field(default_factory=lambda: os.getenv("DATABASE_HOST", "localhost"))
    PORT: str = field(default_factory=lambda: os.getenv("DATABASE_PORT", "1521"))
    SERVICE_NAME: str = field(default_factory=lambda: os.getenv("DATABASE_SERVICE_NAME", "FREEPDB1"))
    DSN: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_DSN",
            f"{os.getenv('DATABASE_HOST', 'localhost')}:{os.getenv('DATABASE_PORT', '1521')}/{os.getenv('DATABASE_SERVICE_NAME', 'FREEPDB1')}",
        )
    )
    POOL_MIN_SIZE: int = field(default_factory=lambda: int(os.getenv("DATABASE_POOL_MIN_SIZE", "5")))
    POOL_MAX_SIZE: int = field(default_factory=lambda: int(os.getenv("DATABASE_POOL_MAX_SIZE", "20")))
    POOL_TIMEOUT: int = field(default_factory=lambda: int(os.getenv("DATABASE_POOL_TIMEOUT", "30")))
    POOL_RECYCLE: int = field(default_factory=lambda: int(os.getenv("DATABASE_POOL_RECYCLE", "300")))

    @property
    def is_autonomous(self) -> bool:
        """Detect if using Autonomous Database."""
        return self.URL is not None and self.WALLET_PASSWORD is not None

    def create_config(self) -> OracleAsyncConfig:
        """Create Oracle database configuration."""
        conn_params = self.get_connection_params()

        if self.is_autonomous:
            if not self.WALLET_LOCATION:
                msg = "WALLET_LOCATION or TNS_ADMIN must be set for Autonomous Database"
                raise ValueError(msg)
            os.environ["TNS_ADMIN"] = self.WALLET_LOCATION

            pool_config = {
                "user": conn_params["user"],
                "password": conn_params["password"],
                "dsn": conn_params["dsn"],
                "wallet_password": conn_params["wallet_password"],
                "min": self.POOL_MIN_SIZE,
                "max": self.POOL_MAX_SIZE,
            }
        else:
            pool_config = {
                "user": conn_params["user"],
                "password": conn_params["password"],
                "dsn": conn_params["dsn"],
                "min": self.POOL_MIN_SIZE,
                "max": self.POOL_MAX_SIZE,
            }

        return OracleAsyncConfig(
            pool_config=pool_config,
            migration_config={
                "version_table_name": "migrations",
                "script_location": self.MIGRATION_PATH,
                "project_root": BASE_DIR,
            },
        )
```

### Application Settings

```python
@dataclass
class AppSettings:
    """Application configuration."""

    URL: str = field(default_factory=lambda: os.getenv("APP_URL", "http://localhost:8000"))
    DEBUG: bool = field(default_factory=lambda: os.getenv("LITESTAR_DEBUG", "False") in TRUE_VALUES)
    SECRET_KEY: str = field(
        default_factory=lambda: os.getenv(
            "SECRET_KEY",
            binascii.hexlify(os.urandom(32)).decode(encoding="utf-8")
        )
    )
    NAME: str = field(default_factory=lambda: "app")
    ALLOWED_CORS_ORIGINS: list[str] | str = field(
        default_factory=lambda: os.getenv("ALLOWED_CORS_ORIGINS", '["*"]')
    )
    GOOGLE_PROJECT_ID: str = field(default_factory=lambda: os.getenv("GOOGLE_PROJECT_ID", ""))
    GEMINI_MODEL: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    EMBEDDING_MODEL: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-004"))

    def __post_init__(self) -> None:
        """Parse ALLOWED_CORS_ORIGINS if it's a JSON string."""
        if isinstance(self.ALLOWED_CORS_ORIGINS, str):
            if self.ALLOWED_CORS_ORIGINS.startswith("["):
                self.ALLOWED_CORS_ORIGINS = json.loads(self.ALLOWED_CORS_ORIGINS)
            else:
                self.ALLOWED_CORS_ORIGINS = [
                    host.strip() for host in self.ALLOWED_CORS_ORIGINS.split(",")
                ]
```

### Vertex AI Settings

```python
@dataclass
class VertexAISettings:
    """Vertex AI configuration settings."""

    PROJECT_ID: str = field(
        default_factory=lambda: os.getenv("VERTEX_AI_PROJECT_ID")
        or os.getenv("GOOGLE_PROJECT_ID")
        or ""
    )
    LOCATION: str = field(default_factory=lambda: os.getenv("VERTEX_AI_LOCATION") or "us-central1")
    API_KEY: str | None = field(
        default_factory=lambda: (
            os.getenv("VERTEX_AI_API_KEY")
            or os.getenv("GOOGLE_AI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("GENAI_API_KEY")
        )
    )
    EMBEDDING_MODEL: str = field(
        default_factory=lambda: os.getenv("VERTEX_AI_EMBEDDING_MODEL")
        or os.getenv("EMBEDDING_MODEL")
        or "text-embedding-004"
    )
    EMBEDDING_DIMENSIONS: int = field(
        default_factory=lambda: int(os.getenv("VERTEX_AI_EMBEDDING_DIMENSIONS", "768"))
    )
    CHAT_MODEL: str = field(
        default_factory=lambda: os.getenv("VERTEX_AI_CHAT_MODEL")
        or os.getenv("GEMINI_MODEL")
        or "gemini-2.5-flash-lite"
    )

    # Context Caching Settings
    CACHE_TTL_SECONDS: int = field(
        default_factory=lambda: int(os.getenv("VERTEX_AI_CACHE_TTL_SECONDS", "3600"))
    )
    CACHE_PREFIX: str = field(default_factory=lambda: os.getenv("VERTEX_AI_CACHE_PREFIX", "cymbal-coffee"))
```

## Usage Patterns

### Accessing Settings

```python
from app.lib.settings import get_settings

# In application code
settings = get_settings()
project_id = settings.vertex_ai.PROJECT_ID
debug_mode = settings.app.DEBUG

# In services
class MyService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.vertex_ai.API_KEY
```

### Environment Variables

**.env file**:
```bash
# Database
DATABASE_USER=app
DATABASE_PASSWORD=super-secret
DATABASE_HOST=localhost
DATABASE_PORT=1521
DATABASE_SERVICE_NAME=FREEPDB1

# Autonomous Database (alternative)
DATABASE_URL=oracle+oracledb://user:password@service_name
WALLET_PASSWORD=wallet-secret
WALLET_LOCATION=/path/to/wallet

# Application
APP_URL=http://localhost:8000
LITESTAR_DEBUG=true
SECRET_KEY=your-secret-key-here
GOOGLE_PROJECT_ID=your-project-id

# Vertex AI
VERTEX_AI_PROJECT_ID=your-project-id
VERTEX_AI_LOCATION=us-central1
EMBEDDING_MODEL=text-embedding-004
GEMINI_MODEL=gemini-2.5-flash

# Agent Configuration
AGENT_INTENT_THRESHOLD=0.8
AGENT_VECTOR_SEARCH_THRESHOLD=0.7
AGENT_VECTOR_SEARCH_LIMIT=5

# Cache Configuration
CACHE_RESPONSE_TTL_MINUTES=5
CACHE_EMBEDDING_ENABLED=True
```

### Testing Configuration

```python
import pytest
from pytest import MonkeyPatch
from app.lib import settings as app_settings

@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    """Patch settings for tests."""
    test_dir = tmp_path_factory.mktemp("test_env")
    test_env = test_dir / ".env.testing"
    test_env.write_text("""
DATABASE_USER=test_app
DATABASE_PASSWORD=test-secret
GOOGLE_PROJECT_ID=test-project
LITESTAR_DEBUG=true
SECRET_KEY=test-secret-key-32-characters-12
""")

    settings = app_settings.Settings.from_env(str(test_env))

    def get_settings(dotenv_filename: str = ".env.testing") -> app_settings.Settings:
        return settings

    monkeypatch.setattr(app_settings, "get_settings", get_settings)
```

## When to Use

### Use Dataclass Settings When:

1. **Type Safety**: You want IDE autocomplete and type checking
2. **Validation**: You need computed properties or post-init validation
3. **Defaults**: You want sensible defaults for all config values
4. **Environment Variables**: You're loading config from environment

### Use Environment Variables Directly When:

1. **Secrets**: Sensitive data that shouldn't be in code
2. **Deployment**: Different values per environment
3. **Docker/K8s**: Configuration via container environment

## Best Practices

1. **Always use `get_settings()`** - it's cached, singleton pattern
2. **Provide defaults** for development/testing
3. **Use `field(default_factory=lambda: ...)` for dynamic defaults
4. **Document environment variables** in README and .env.example
5. **Validate critical settings** in `__post_init__`
6. **Use type hints** for all fields
7. **Group related settings** in separate dataclasses

## Common Patterns

### Feature Flags

```python
@dataclass
class AppSettings:
    FEATURE_NEW_UI: bool = field(
        default_factory=lambda: os.getenv("FEATURE_NEW_UI", "False") in TRUE_VALUES
    )
    FEATURE_EXPERIMENTAL: bool = field(
        default_factory=lambda: os.getenv("FEATURE_EXPERIMENTAL", "False") in TRUE_VALUES
    )
```

### Connection String Building

```python
@dataclass
class DatabaseSettings:
    @property
    def connection_string(self) -> str:
        """Build connection string from components."""
        if self.is_autonomous:
            return self.URL
        return f"oracle+oracledb://{self.USER}:{self.PASSWORD}@{self.DSN}"
```

### Multi-Environment Support

```python
@dataclass
class AppSettings:
    ENVIRONMENT: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
```

## Common Gotchas

1. **Mutable defaults**: Use `field(default_factory=...)` not direct assignment
   ```python
   # BAD
   ALLOWED_ORIGINS: list[str] = ["*"]  # Shared across instances!

   # GOOD
   ALLOWED_ORIGINS: list[str] = field(default_factory=lambda: ["*"])
   ```

2. **Type conversion**: Environment variables are always strings
   ```python
   # BAD
   PORT: int = os.getenv("PORT", 8000)  # Returns string "8000"!

   # GOOD
   PORT: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
   ```

3. **Boolean parsing**: Use TRUE_VALUES constant
   ```python
   TRUE_VALUES = {"True", "true", "1", "yes", "Y", "T"}

   # GOOD
   DEBUG: bool = field(
       default_factory=lambda: os.getenv("DEBUG", "False") in TRUE_VALUES
   )
   ```

4. **Circular imports**: Import settings module, not individual settings
   ```python
   # BAD
   from app.lib.settings import Settings  # Might cause circular import

   # GOOD
   from app.lib.settings import get_settings
   settings = get_settings()
   ```
