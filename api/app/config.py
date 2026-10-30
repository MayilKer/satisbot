from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    qdrant_url: str
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-5-5"
    voyage_api_key: str = ""
    embedding_model: str = "voyage-4"
    rerank_model: str = "rerank-2.5"


settings = Settings()