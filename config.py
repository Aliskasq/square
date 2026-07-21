"""Configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3n-e4b-it:free")

_runtime = {
    "api_key": OPENROUTER_API_KEY,
    "model": OPENROUTER_MODEL,
}


def get_api_key() -> str:
    return _runtime["api_key"]


def set_api_key(key: str):
    _runtime["api_key"] = key
    _save_env("OPENROUTER_API_KEY", key)


def get_model() -> str:
    return _runtime["model"]


def set_model(model: str):
    _runtime["model"] = model
    _save_env("OPENROUTER_MODEL", model)


def _save_env(key: str, value: str):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{key}={value}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)
