import os


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://wodgod:wodgod_dev@localhost:5432/wodgod"
    )
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")

    # Default user ID (single-user system)
    DEFAULT_USER_ID: str = "11111111-1111-1111-1111-111111111111"


settings = Settings()
