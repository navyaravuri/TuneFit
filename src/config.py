import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-70b-8192")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")


def get_provider() -> str:
    return LLM_PROVIDER if LLM_PROVIDER in ("groq", "ollama") else "groq"


def setup_logging() -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(logs_dir / "tunefit.log"),
        ],
    )
