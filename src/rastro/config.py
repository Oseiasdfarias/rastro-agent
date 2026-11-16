from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://rastro:rastro@localhost:55490/rastro"
    redis_url: str | None = None
    llm_models: Annotated[list[str], NoDecode] = ["ollama/qwen2.5:3b"]
    ollama_base_url: str = "http://host.docker.internal:11434"
    max_steps: int = 8
    ollama_num_ctx: int = 16384
    embed_model: str = "intfloat/multilingual-e5-small"
    langfuse_enabled: bool = False
    llm_cache: bool = True

    @field_validator("llm_models", mode="before")
    @classmethod
    def _split(cls, v: object) -> object:
        if isinstance(v, str):
            return [m.strip() for m in v.split(",") if m.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
