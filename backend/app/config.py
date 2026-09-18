from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        extra="ignore",
    )

    database_url: str = "postgresql://sentinelpay:sentinelpay@localhost:5432/sentinelpay"
    jwt_secret: str = "change-me-in-production-sentinelpay"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720
    ipapi_base_url: str = "https://ipapi.co"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
