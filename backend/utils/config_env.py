from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

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


settings = Settings()
