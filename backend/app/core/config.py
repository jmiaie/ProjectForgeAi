from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ProjectForge AI"
    DEPLOYMENT_MODE: Literal["saas", "hybrid", "onprem"] = "saas"
    DEFAULT_COMPLIANCE: str = "standard"
    DEFAULT_LLM_MODEL: str = "groq/llama-3.1-70b-versatile"
    NEO4J_URI: str = "bolt://neo4j:7687"
    POSTGRES_URI: str = "postgresql://projectforge:projectforge@postgres:5432/projectforge"
    ENCRYPTION_KEY: str = "dev-only-change-me"
    LOCUS_SOURCE_PATH: str | None = None
    LOCUS_ENGINE: str = "locus:LocusEngine"
    LOCUS_STORE_ROOT: str = "./.locus"
    OMPA_SOURCE_PATH: str | None = None
    OMPA_ENGINE: str = "ompa:Ompa"
    OMPA_VAULT_ROOT: str = "./vaults"
    REQUIRE_NATIVE_LOCUS_OMPA: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
