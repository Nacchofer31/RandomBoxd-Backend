"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "RandomBoxd Backend"
    app_env: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://randomboxd:randomboxd@localhost:5432/randomboxd"

    # LLM / AI
    llm_provider: str = "openai"  # openai | gemini | claude | openrouter | ollama

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Google Gemini
    google_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Anthropic Claude
    anthropic_api_key: str = ""
    claude_model: str = "claude-3-haiku-20240307"

    # OpenRouter (aggregator)
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Logging
    log_level: str = "INFO"


# Global settings instance
settings = Settings()
