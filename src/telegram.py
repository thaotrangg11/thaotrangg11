"""Telegram Bot API wrapper — dùng fetch của Cloudflare."""
from js import fetch, Headers, Object
from pyodide.ffi import to_js
import json

API = "https://api.telegram.org/bot"

async def _post(token: str, method: str, payload: dict) -> dict:
    headers = Headers.new()
    headers.set("content-type", "application/json")
    resp = await fetch(
        f"{API}{token}/{method}",
        Object.fromEntries(to_js({
            "method": "POST",
            "headers": headers,
            "body": json.dumps(payload),
        }))
    )
    text = await resp.text()
    try:
        return json.loads(text)
    except Exception:
        return {"ok": False, "raw": text}

async def send_message(token: str, chat_id: int, text: str,
                       parse_mode: str | None = "HTML",
                       reply_markup: dict | None = None,
                       reply_to: int | None = None) -> dict:
    payload = {"chat_id": chat_id, "text": text[:4096]}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    return await _post(token, "sendMessage", payload)

async def edit_message(token: str, chat_id: int, message_id: int,
                       text: str, parse_mode: str | None = "HTML") -> dict:
    return await _post(token, "editMessageText", {
        "chat_id": chat_id, "message_id": message_id,
        "text": text[:4096], "parse_mode": parse_mode,
    })

async def answer_callback(token: str, cb_id: str, text: str = "") -> dict:
    return await _post(token, "answerCallbackQuery",
                       {"callback_query_id": cb_id, "text": text})
