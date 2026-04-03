from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Restaurant Decision Assistant"
    app_env: str = "development"
    app_version: str = "0.1.0"
    app_docs_url: str = "/docs"
    app_redoc_url: str = "/redoc"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_port: int = 3000
    cors_allow_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_allow_headers: str = "*"
    database_url: str = "sqlite:///./backend/data/app.db"
    database_auto_seed: bool = True
    sample_businesses_path: str = "backend/data/samples/demo_businesses.jsonl"
    sample_reviews_path: str = "backend/data/samples/demo_reviews.jsonl"
    llm_provider: str = "stub"
    llm_model_name: str = "stub-chat-model"
    llm_temperature: float = 0.0
    llm_max_tokens: int | None = 256
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    chat_system_prompt: str = (
        "You are a concise assistant inside the AI Restaurant Decision Assistant backend. "
        "Answer directly and keep the response grounded in the conversation."
    )
    stub_llm_response_prefix: str = "Stub reply: "
    stub_llm_default_reply: str = "Hello from the stub model."

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

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allow_origins.split(",") if item.strip()]

    @property
    def cors_methods_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allow_methods.split(",") if item.strip()]

    @property
    def cors_headers_list(self) -> list[str]:
        if self.cors_allow_headers.strip() == "*":
            return ["*"]
        return [item.strip() for item in self.cors_allow_headers.split(",") if item.strip()]


settings = Settings()
