from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ProjectForge AI"
    DEPLOYMENT_MODE: Literal["saas", "hybrid", "onprem"] = "saas"
    DEFAULT_COMPLIANCE: str = "standard"
    DEFAULT_LLM_MODEL: str = "groq/llama-3.1-70b-versatile"
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "projectforge"
    POSTGRES_URI: str = "postgresql+psycopg://projectforge:projectforge@postgres:5432/projectforge"
    ENCRYPTION_KEY: str = "replace-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
