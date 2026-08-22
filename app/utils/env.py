from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


def load_local_env() -> None:
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
