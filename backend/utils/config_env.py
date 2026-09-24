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

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_comma_separated(cls, value):
        """Accept "a,b" from .env, since pydantic-settings expects JSON for lists."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
