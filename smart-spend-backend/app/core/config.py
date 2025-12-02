from functools import lru_cache

from arq.connections import RedisSettings
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="smart-spend-backend/.env")
    
    # === SECURITY ===
    # Using SecretStr for sensitive data is a Pydantic best practice
    SECRET_KEY: SecretStr = Field(..., json_schema_extra={"env": "SECRET_KEY"})
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Now loaded from .env default in .env is 60

    # We MUST define the ALGORITHM field since it exists in the .env file
    ALGORITHM: str = Field(..., json_schema_extra={"env": "ALGORITHM"})

    # === DATABASE ===
    DATABASE_URL: str = Field(..., json_schema_extra={"env": "DATABASE_URL"})

    # === REDIS (ARQ Worker) ===
    REDIS_HOST: str = Field(..., json_schema_extra={"env": "REDIS_HOST"})
    REDIS_PORT: int = Field(..., json_schema_extra={"env": "REDIS_PORT"})
    REDIS_DB: int = Field(..., json_schema_extra={"env": "REDIS_DB"})
    REDIS_PASSWORD: str = Field(..., json_schema_extra={"env": "REDIS_PASSWORD"})

    @property
    def REDIS_SETTINGS(self) -> RedisSettings:
        """
        Return ARQ-compatible Redis settings object.
        """
        return RedisSettings(
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            database=self.REDIS_DB,
            password=self.REDIS_PASSWORD,
        )

    # === HuggingFace ===
    HF_TOKEN: str = Field("", json_schema_extra={"env": "HF_TOKEN"})

    # We MUST define the ENV field since it exists in the .env file
    ENV: str = Field("development", json_schema_extra={"env": "ENV"})


@lru_cache()
def get_settings() -> Settings:
    """
    Function to load settings with caching.
    """
    return Settings()

settings = get_settings()