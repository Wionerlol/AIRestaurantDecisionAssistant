from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Restaurant Decision Assistant"
    app_env: str = "development"
    database_url: str = "sqlite:///./backend/data/app.db"
    database_auto_seed: bool = True
    sample_businesses_path: str = "backend/data/samples/demo_businesses.jsonl"
    sample_reviews_path: str = "backend/data/samples/demo_reviews.jsonl"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[4]

    @property
    def sample_businesses_file(self) -> Path:
        return self.project_root / self.sample_businesses_path

    @property
    def sample_reviews_file(self) -> Path:
        return self.project_root / self.sample_reviews_path


settings = Settings()
