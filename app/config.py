import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "CBAM-Ready Emissions Passport"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Base Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    SAMPLE_DOCS_DIR: Path = BASE_DIR / "data" / "sample_docs"
    REPORT_OUTPUT_DIR: Path = BASE_DIR / "data" / "reports"
    RAG_DATA_DIR: Path = BASE_DIR / "data" / "regulatory_docs"
    FAISS_INDEX_DIR: Path = BASE_DIR / "data" / "faiss_index"

    # SQLite Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/cbam_passport.db"

    # LLM Settings (OpenAI / Ollama / Open-source fallback)
    LLM_PROVIDER: str = "local"  # "local", "ollama", "openai"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

    # Embeddings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Ensure runtime directories exist
for path in [
    settings.DATA_DIR,
    settings.UPLOAD_DIR,
    settings.SAMPLE_DOCS_DIR,
    settings.REPORT_OUTPUT_DIR,
    settings.RAG_DATA_DIR,
    settings.FAISS_INDEX_DIR,
]:
    path.mkdir(parents=True, exist_ok=True)
