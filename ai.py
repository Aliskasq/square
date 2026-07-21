"""OpenRouter AI chat."""
import logging
import os
import httpx
from config import get_api_key, get_model, switch_to_next_key, get_active_key_index, get_all_keys

logger = logging.getLogger(__name__)

# Per-user conversation history
_histories: dict[int, list[dict]] = {}

MAX_HISTORY = 40  # max messages in context

# System prompt from Prompt.txt
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "Prompt.txt")


def _load_system_prompt() -> str:
    """Load system prompt from Prompt.txt."""
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def get_history(user_id: int) -> list[dict]:
    if user_id not in _histories:
        _histories[user_id] = []
    return _histories[user_id]


def clear_history(user_id: int):
    _histories[user_id] = []


async def chat(user_id: int, text: str) -> str:
    """Send message to AI, return response."""
    api_key = get_api_key()
    model = get_model()

    if not api_key:
        return "❌ API ключ не установлен. /key"

    history = get_history(user_id)
    history.append({"role": "user", "content": text})

    # Trim history
    if len(history) > MAX_HISTORY:
        history[:] = history[-MAX_HISTORY:]

    # Build messages with system prompt
    messages = []
    system_prompt = _load_system_prompt()
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history)

    start_key_idx = get_active_key_index()
    tried_keys = 0
    total_keys = len(get_all_keys())

    while tried_keys < total_keys:
        current_key = get_api_key()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {current_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                    },
                    timeout=120,
                )

                # Rate limited — try next key
                if resp.status_code == 429:
                    tried_keys += 1
                    if switch_to_next_key():
                        logger.info(f"Key rate limited, switching to key #{get_active_key_index() + 1}")
                        continue
                    history.pop()
                    return "❌ Все ключи исчерпали лимит. Попробуй позже."

                if resp.status_code != 200:
                    history.pop()
                    return f"❌ Выбранная модель недоступна (HTTP {resp.status_code})"

                data = resp.json()

                if "error" in data:
                    err_code = data["error"].get("code")
                    if err_code == 429:
                        tried_keys += 1
                        if switch_to_next_key():
                            logger.info(f"Key rate limited, switching to key #{get_active_key_index() + 1}")
                            continue
                        history.pop()
                        return "❌ Все ключи исчерпали лимит. Попробуй позже."
                    history.pop()
                    err_msg = data["error"].get("message", "unknown error")
                    return f"❌ Выбранная модель недоступна: {err_msg}"

                choices = data.get("choices") or [{}]
                msg = choices[0].get("message") or {}
                content = msg.get("content") or ""

                if not content:
                    history.pop()
                    return "❌ Выбранная модель недоступна (пустой ответ)"

                history.append({"role": "assistant", "content": content})
                return content

        except httpx.TimeoutException:
            history.pop()
            return "❌ Выбранная модель недоступна (таймаут)"
        except Exception as e:
            history.pop()
            logger.error(f"AI error: {e}")
            return f"❌ Выбранная модель недоступна: {e}"

    history.pop()
    return "❌ Все ключи исчерпали лимит. Попробуй позже."
