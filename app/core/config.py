from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/authdb"
    jwt_secret: SecretStr = SecretStr("change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_min: int = 30
    refresh_token_expire_days: int = 7
    otp_expire_min: int = 5
    otp_max_resend_per_hour: int = 3
    register_max_per_hour: int = 5
    login_max_per_15_min: int = 10
    resend_api_key: SecretStr = SecretStr("")
    email_from: str = "onboarding@example.com"
    cors_origins: list[str] = ["http://localhost:3000"]

    def production_warnings(self) -> list[str]:
        warnings: list[str] = []
        if self.jwt_secret.get_secret_value() == "change-me":
            warnings.append("JWT_SECRET uses the insecure default")
        if not self.resend_api_key.get_secret_value():
            warnings.append("RESEND_API_KEY is unset; emails will not be delivered")
        if self.email_from.endswith("@example.com"):
            warnings.append("EMAIL_FROM is still an example address")
        return warnings


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
