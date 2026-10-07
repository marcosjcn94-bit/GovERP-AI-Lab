from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="GOVERP_", extra="ignore")

    owner_database_url: str = "postgresql+psycopg://goverp_owner:local@127.0.0.1:5440/goverp"
    app_database_url: str = "postgresql+psycopg://goverp_app:local@127.0.0.1:5440/goverp"
    session_secret: str = ""
    model_url: str = "http://127.0.0.1:11434"
    model_name: str = "qwen3:4b"
    model_timeout_seconds: float = Field(default=120, ge=1, le=180)
    allowed_origin: str = "http://127.0.0.1:5173"


settings = Settings()
