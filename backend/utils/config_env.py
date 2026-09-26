import os
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

class Settings(BaseSettings):
    port: int = 8000
    anthropic_api_key: SecretStr = Field(..., validation_alias="ANTHROPIC_API_KEY")
    debug: bool = False
    env: str = "development"
    # Optional: opening the sheet by id only needs the Sheets API,
    # while opening it by name also requires the Drive API.
    google_sheet_id: str = Field("", validation_alias="GOOGLE_SHEET_ID")
    # Only needed when the API key is not scoped to a workspace.
    anthropic_workspace_id: str = Field("", validation_alias="ANTHROPIC_WORKSPACE_ID")
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    # NoDecode stops pydantic-settings from trying to JSON-parse the value,
    # so the validator below can accept a plain comma-separated string.
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"],
        validation_alias="ALLOWED_ORIGINS",
        description="Comma-separated list of allowed origins for CORS",
    )
    langsmith_tracing: bool = Field(False, validation_alias="LANGSMITH_TRACING")
    langsmith_endpoint: str = Field(
        "https://api.smith.langchain.com", validation_alias="LANGSMITH_ENDPOINT")
    langsmith_api_key: SecretStr = Field("", validation_alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field("InvoiceRecord", validation_alias="LANGSMITH_PROJECT")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_comma_separated(cls, value):
        """Accept "a,b" from .env, since pydantic-settings expects JSON for lists."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()

# LangSmith and LangChain read their configuration from os.environ, and
# pydantic-settings does not export .env values there. Without this block the
# values above are loaded but tracing stays silently disabled.
if settings.langsmith_tracing:
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_ENDPOINT", settings.langsmith_endpoint)
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key.get_secret_value())
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
