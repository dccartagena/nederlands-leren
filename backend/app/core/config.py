from pathlib import Path

from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
REPO_ROOT = BACKEND_DIR.parent  # project root


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = f"sqlite:///{REPO_ROOT}/data/app.db"

    # Directories
    AUDIO_DIR: Path = REPO_ROOT / "data" / "audio"
    DATA_DIR: Path = REPO_ROOT / "data"

    # LLM — Gemini primary, Ollama local fallback
    LLM_PROVIDER: str = "gemini"  # "gemini" | "ollama"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TTS_MODEL: str = "gemini-2.5-flash-preview-tts"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "mistral:7b-instruct-q4_K_M"

    # Images
    PIXABAY_API_KEY: str = ""

    # App
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False

    class Config:
        env_file = str(REPO_ROOT / ".env")
        case_sensitive = True
        extra = "ignore"


settings = Settings()
