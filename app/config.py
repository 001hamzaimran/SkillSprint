from pathlib import Path
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore", populate_by_name=True)
    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"
    app_secret_key: str = Field(
        min_length=32, validation_alias=AliasChoices("APP_SECRET_KEY", "SECRET_KEY")
    )
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGODB_URI", "MONGO_URI"),
    )
    mongodb_db_name: str = "skillsprint"
    genai_provider: str = "openai"
    openai_api_key: str = Field(
        default="", validation_alias=AliasChoices("OPENAI_API_KEY", "GENAI_API_KEY")
    )
    genai_model: str = "gpt-4.1-mini"
    session_cookie_secure: bool = False
    port: int = 8000
    upload_dir: Path = ROOT / "uploads"
    max_upload_mb: int = Field(default=10, ge=1, le=25)
    run_worker: bool = True
    bootstrap_admin_email: str = "admin@skillsprint.local"
    bootstrap_admin_password: str = ""

    @model_validator(mode="after")
    def production_security(self):
        if self.app_env == "production" and (
            not self.session_cookie_secure or not self.app_base_url.startswith("https://")
        ):
            raise ValueError("Production requires HTTPS and secure session cookies.")
        if self.genai_provider != "openai":
            raise ValueError("This workspace supports the OpenAI provider only.")
        self.upload_dir = self.upload_dir.resolve()
        return self
