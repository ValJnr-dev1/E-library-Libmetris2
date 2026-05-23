from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://elibrary:elibrary_secret@localhost:5432/elibrary"

    jwt_secret: str = "change-me"
    jwt_expiry_minutes: int = 60
    jwt_algorithm: str = "HS256"

    upload_directory: str = "/app/uploads"
    max_upload_size_mb: int = 25

    login_rate_limit: int = 10
    login_rate_window_seconds: int = 60

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
