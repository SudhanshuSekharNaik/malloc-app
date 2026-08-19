"""
Central configuration for malloc().

Stage 1 note: everything here is deliberately minimal. Do not add
memory-related settings until Stage 3+ actually needs them.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "groq" (free, no billing) or "anthropic" (paid, needs billing on console.anthropic.com)
    llm_provider: str = "groq"

    anthropic_api_key: str = ""
    memora_model: str = "claude-sonnet-5"

    groq_api_key: str = ""
    groq_model: str = "groq/compound-mini"

    database_url: str = "sqlite:///./memora.db"

    # Google OAuth2 Credentials (for Gmail API integration with gmail.send scope)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/outreach/gmail/callback"


settings = Settings()
