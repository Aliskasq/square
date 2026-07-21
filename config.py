"""Configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_KEY_2 = os.getenv("OPENROUTER_API_KEY_2", "")
OPENROUTER_API_KEY_3 = os.getenv("OPENROUTER_API_KEY_3", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3n-e4b-it:free")

# Build list of available keys
_all_keys = [k for k in [OPENROUTER_API_KEY, OPENROUTER_API_KEY_2, OPENROUTER_API_KEY_3] if k]

_runtime = {
    "api_keys": _all_keys,
    "active_key_idx": 0,
    "model": OPENROUTER_MODEL,
}


def get_api_key() -> str:
    keys = _runtime["api_keys"]
    if not keys:
        return ""
    idx = _runtime["active_key_idx"]
    return keys[idx % len(keys)]


def get_all_keys() -> list[str]:
    return list(_runtime["api_keys"])


def get_active_key_index() -> int:
    return _runtime["active_key_idx"]


def switch_to_next_key() -> bool:
    """Switch to next key. Returns True if switched, False if no more keys."""
    keys = _runtime["api_keys"]
    if len(keys) <= 1:
        return False
    _runtime["active_key_idx"] = (_runtime["active_key_idx"] + 1) % len(keys)
    return True


def set_api_key(key: str):
    _runtime["api_keys"] = [key] + [k for k in _runtime["api_keys"] if k != key]
    _runtime["active_key_idx"] = 0
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
