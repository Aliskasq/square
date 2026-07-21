"""Telegram bot handlers."""
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from config import ADMIN_ID, get_api_key, set_api_key, get_model, set_model
from ai import chat, clear_history

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# --- Commands ---

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "🟧 Square AI Bot\n\n"
        "Просто пиши — я отвечу через AI.\n\n"
        "/models — выбрать модель\n"
        "/model — текущая модель\n"
        "/key ключ — сменить API ключ\n"
        "/clear — очистить историю\n"
        "/status — статус",
    )


async def cmd_model(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(f"🤖 Модель: {get_model()}")


async def cmd_key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not ctx.args:
        current = get_api_key()
        masked = current[:10] + "..." + current[-4:] if len(current) > 14 else "не установлен"
        return await update.message.reply_text(f"🔑 Ключ: {masked}\n\nСменить: /key новый_ключ")
    set_api_key(ctx.args[0].strip())
    await update.message.reply_text("✅ API ключ обновлён")


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    clear_history(update.effective_user.id)
    await update.message.reply_text("🗑 История очищена")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    from ai import get_history
    history = get_history(update.effective_user.id)
    await update.message.reply_text(
        f"📊 Статус\n\n"
        f"Модель: {get_model()}\n"
        f"Сообщений в контексте: {len(history)}\n"
        f"API ключ: {'✅' if get_api_key() else '❌'}",
    )


# --- Models ---

async def _fetch_free_models() -> list[dict]:
    """Fetch free models from OpenRouter API."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://openrouter.ai/api/v1/models", timeout=15)
            r.raise_for_status()
            data = r.json()
        free = []
        for m in data.get("data", []):
            pricing = m.get("pricing", {})
            prompt_cost = float(pricing.get("prompt", "1") or "1")
            completion_cost = float(pricing.get("completion", "1") or "1")
            if prompt_cost == 0 and completion_cost == 0:
                free.append({
                    "id": m["id"],
                    "name": m.get("name", m["id"]),
                    "context": m.get("context_length", 0),
                })
        free.sort(key=lambda x: x["name"].lower())
        return free
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        return []


async def cmd_models(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    # If argument given — set model directly
    if ctx.args:
        model_name = " ".join(ctx.args).strip()
        set_model(model_name)
        return await update.message.reply_text(f"✅ Модель: {model_name}")

    msg = await update.message.reply_text("⏳ Загружаю бесплатные модели...")

    free = await _fetch_free_models()
    if not free:
        return await msg.edit_text("❌ Не удалось загрузить модели")

    current = get_model()

    # Build buttons (2 per row)
    buttons = []
    row = []
    for m in free:
        short = m["id"].replace(":free", "").split("/")[-1]
        marker = "✅ " if m["id"] == current else ""
        label = f"{marker}{short}"
        cb_data = f"setm:{m['id']}"
        if len(cb_data.encode()) > 64:
            cb_data = cb_data[:64]
        row.append(InlineKeyboardButton(label, callback_data=cb_data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    text = (
        f"🤖 Активная: {current}\n"
        f"🆓 Бесплатных: {len(free)}\n\n"
        f"Выбери модель 👇"
    )

    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def callback_model_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle model selection from buttons."""
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("⛔")
        return

    model_id = query.data.split(":", 1)[1]
    set_model(model_id)
    clear_history(query.from_user.id)
    await query.answer(f"✅ {model_id}")

    # Update buttons
    old_markup = query.message.reply_markup
    if old_markup:
        new_buttons = []
        for brow in old_markup.inline_keyboard:
            new_row = []
            for btn in brow:
                cb = btn.callback_data or ""
                if cb.startswith("setm:"):
                    btn_model = cb.split(":", 1)[1]
                    short = btn_model.replace(":free", "").split("/")[-1]
                    marker = "✅ " if btn_model == model_id else ""
                    new_row.append(InlineKeyboardButton(
                        f"{marker}{short}", callback_data=cb
                    ))
                else:
                    new_row.append(btn)
            new_buttons.append(new_row)
        try:
            import re
            old_text = query.message.text or ""
            new_text = re.sub(
                r"🤖 Активная: .+",
                f"🤖 Активная: {model_id}",
                old_text,
            )
            await query.edit_message_text(
                new_text,
                reply_markup=InlineKeyboardMarkup(new_buttons),
            )
        except Exception:
            pass


# --- Message handler ---

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages — send to AI."""
    if not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if not text:
        return

    # Send typing action
    await update.message.chat.send_action("typing")

    response = await chat(update.effective_user.id, text)

    # Split long messages
    if len(response) <= 4096:
        await update.message.reply_text(response)
    else:
        for i in range(0, len(response), 4096):
            await update.message.reply_text(response[i:i + 4096])


# --- Setup ---

def setup_handlers(app: Application):
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("models", cmd_models))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("key", cmd_key))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CallbackQueryHandler(callback_model_select, pattern=r"^setm:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
