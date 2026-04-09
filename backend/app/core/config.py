from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List


BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
REPO_ROOT = BACKEND_DIR.parent  # project root


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = f"sqlite:///{REPO_ROOT}/data/app.db"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:80", "http://localhost"]

    # Directories
    AUDIO_DIR: Path = REPO_ROOT / "data" / "audio"
    DATA_DIR: Path = REPO_ROOT / "data"

    # LLM — Ollama local is primary; remote key is optional fallback
    LLM_PROVIDER: str = "ollama"  # "ollama" | "openai" | "anthropic" | "mistral" | "gemini"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "mistral:7b-instruct-q4_K_M"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    REMOTE_MODEL: str = "gpt-4o-mini"
    GEMINI_MODEL: str = "gemini/gemini-2.0-flash"

    # Images
    PIXABAY_API_KEY: str = ""

    # App
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False

    class Config:
        env_file = str(REPO_ROOT / ".env")  # project root instead of cwd
        case_sensitive = True


settings = Settings()
