"""Envia un mensaje a Telegram (boletin diario de la Porra Mundial 2026).

Credenciales en LOCAL (nunca en el repo):
  ~/.config/porra/telegram.token      -> token del bot (de @BotFather)
  ~/.config/porra/telegram_chat_id    -> tu chat id (numero)
o variables de entorno TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID.

Uso:
  python scripts/notify_telegram.py "texto del mensaje"
  echo "texto" | python scripts/notify_telegram.py
"""
from __future__ import annotations

import os
import pathlib
import sys
import urllib.parse
import urllib.request

CFG = pathlib.Path.home() / ".config" / "porra"


def _read(env: str, fname: str) -> str:
    v = os.environ.get(env)
    if v:
        return v.strip()
    f = CFG / fname
    return f.read_text(encoding="utf-8").strip() if f.exists() else ""


def send(msg: str) -> int:
    token = _read("TELEGRAM_BOT_TOKEN", "telegram.token")
    chat = _read("TELEGRAM_CHAT_ID", "telegram_chat_id")
    if not token or not chat:
        sys.exit("❌ Falta token o chat id en ~/.config/porra/ (telegram.token / telegram_chat_id)")
    data = urllib.parse.urlencode({
        "chat_id": chat,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status


def main() -> None:
    msg = " ".join(sys.argv[1:]).strip()
    if not msg and not sys.stdin.isatty():
        msg = sys.stdin.read().strip()
    if not msg:
        sys.exit("❌ Sin mensaje que enviar")
    print("Telegram ->", send(msg))


if __name__ == "__main__":
    main()
