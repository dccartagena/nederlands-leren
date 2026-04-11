from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
REPO_ROOT = BACKEND_DIR.parent  # project root


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = f"sqlite:///{REPO_ROOT}/data/app.db"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:80", "http://localhost"]

    # Directories
    AUDIO_DIR: Path = REPO_ROOT / "data" / "audio"
    DATA_DIR: Path = REPO_ROOT / "data"

    # LLM — Ollama local is primary; Gemini is remote fallback
    LLM_PROVIDER: str = "ollama"  # "ollama" | "gemini"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "mistral:7b-instruct-q4_K_M"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini/gemini-2.0-flash"
    GEMINI_TTS_MODEL: str = "gemini-2.5-flash-preview-tts"

    # Images
    PIXABAY_API_KEY: str = ""

    # App
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        if self.SECRET_KEY == "change-me-in-production":
            raise ValueError(
                "SECRET_KEY must be changed from the default value before running the application. "
                "Set a strong random value in your .env file: SECRET_KEY=<random-64-char-string>"
            )
        return self

    class Config:
        env_file = str(REPO_ROOT / ".env")  # project root instead of cwd
        case_sensitive = True
        extra = "ignore"


settings = Settings()
