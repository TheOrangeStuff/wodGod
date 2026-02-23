import os


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://wodgod:wodgod_dev@localhost:5432/wodgod"
    )
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "72"))


settings = Settings()
