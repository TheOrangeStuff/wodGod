import os


def _build_database_url() -> str:
    """Build DATABASE_URL from individual POSTGRES_* env vars, or use
    DATABASE_URL directly if provided."""
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    user = os.getenv("POSTGRES_USER", "wodgod")
    password = os.getenv("POSTGRES_PASSWORD", "wodgod_dev")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "wodgod")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


class Settings:
    DATABASE_URL: str = _build_database_url()

    # Individual credential components (used by bootstrap)
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "wodgod")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "wodgod_dev")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "wodgod")

    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")

    # Claude API (Anthropic)
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    # Active LLM selection (runtime-switchable, defaults to LLM_PROVIDER)
    active_llm: str = os.getenv("LLM_PROVIDER", "ollama")

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "72"))


settings = Settings()
