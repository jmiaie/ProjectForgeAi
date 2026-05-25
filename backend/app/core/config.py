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
    NEO4J_BOOTSTRAP_ON_CONNECT: bool = True
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
    AUTOMATION_MAX_RETRIES: int = 3
    AUTOMATION_RETRY_BACKOFF_SECONDS: int = 60
    TEMPORAL_ADDRESS: str = "localhost:7233"
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "projectforge-automations"
    TEMPORAL_USE_WORKER_DISPATCH: bool = False
    TEMPORAL_SYNC_SCHEDULES: bool = False
    OAUTH_MOCK_TOKEN_EXCHANGE: bool = True
    OAUTH_ALLOW_UNVERIFIED_STATE: bool = False
    GOOGLE_OAUTH_CLIENT_ID: str | None = None
    GOOGLE_OAUTH_CLIENT_SECRET: str | None = None
    MICROSOFT_OAUTH_CLIENT_ID: str | None = None
    MICROSOFT_OAUTH_CLIENT_SECRET: str | None = None
    GITHUB_OAUTH_CLIENT_ID: str | None = None
    GITHUB_OAUTH_CLIENT_SECRET: str | None = None
    SLACK_OAUTH_CLIENT_ID: str | None = None
    SLACK_OAUTH_CLIENT_SECRET: str | None = None
    USE_LANGGRAPH_ORCHESTRATOR: bool = False
    USE_LANGGRAPH_BRANCHING: bool = True
    IMAGE_OCR_ENABLED: bool = True
    IMAGE_OCR_TIMEOUT_SECONDS: int = 30
    TESSERACT_CMD: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
