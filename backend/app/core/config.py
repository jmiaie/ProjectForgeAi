from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ProjectForge AI"
    DEPLOYMENT_MODE: Literal["saas", "hybrid", "onprem"] = "saas"
    DEFAULT_COMPLIANCE: str = "standard"
    DEFAULT_LLM_MODEL: str = "groq/llama-3.1-70b-versatile"
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "projectforge-password"
    NEO4J_CONNECTION_TIMEOUT: float = 1.0
    REQUIRE_NATIVE_NEO4J: bool = False
    POSTGRES_URI: str = "postgresql://projectforge:projectforge@postgres:5432/projectforge"
    ENCRYPTION_KEY: str = "dev-only-change-me"
    LOCUS_SOURCE_PATH: str | None = None
    LOCUS_ENGINE: str = "locus:LocusEngine"
    LOCUS_STORE_ROOT: str = "./.locus"
    OMPA_SOURCE_PATH: str | None = None
    OMPA_ENGINE: str = "ompa:Ompa"
    OMPA_VAULT_ROOT: str = "./vaults"
    REQUIRE_NATIVE_LOCUS_OMPA: bool = False
    INGESTION_MANIFEST_ROOT: str = "./.ingestion"
    ORCHESTRATION_RUN_ROOT: str = "./.orchestrator"
    COMPLIANCE_PROFILE_ROOT: str = "./.compliance"
    COMPLIANCE_AUDIT_ROOT: str = "./.audit"
    INTEGRATIONS_CONNECTION_ROOT: str = "./.connections"
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    BACKEND_BASE_URL: str = "http://localhost:8000"
    AUTOMATION_WORKFLOW_ROOT: str = "./.automations"
    TEMPORAL_ADDRESS: str = "localhost:7233"
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "projectforge-automations"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
