#!/usr/bin/env python3
"""UserPromptSubmit hook'u: kullanıcı mesajını docs/kayit/inputlar.md sonuna ekler.

- Alt agent turlarını (agent_id varsa) kaydetmez.
- Kullanıcı turu olarak gelen sistem/agent iletilerini (<agent-message>, <task-notification> …) kaydetmez.
- "kayıt tutma" / "bu inputumu yok say" içeren mesajları kaydetmez.
- 500 karakterden uzun mesajları kısaltır; token/anahtar benzeri dizileri maskeler.
Başlıktaki "kısa başlık" otomatik üretilir; orkestratör gerekirse düzeltir.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SKIP = ("kayıt tutma", "kayit tutma", "bu inputumu yok say")
SYSTEM_PREFIXES = (
    "<agent-message", "<task-notification", "<system-reminder",
    "<side-sessions-event", "<ci-monitor-event",
)
SECRET = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|"
    r"(?i:(api[_-]?key|token|password|şifre)\s*[:=]\s*)\S+)"
)
LIMIT = 500


def main() -> None:
    data = json.load(sys.stdin)
    if data.get("agent_id"):
        return
    prompt: str = (data.get("prompt") or "").strip()
    if not prompt or any(s in prompt.lower() for s in SKIP):
        return
    if prompt.startswith(SYSTEM_PREFIXES):
        return

    prompt = SECRET.sub("[GİZLİ]", prompt)
    title = re.sub(r"\s+", " ", prompt.splitlines()[0])[:60].rstrip()
    body = prompt
    if len(body) > LIMIT:
        body = body[:LIMIT].rstrip() + f" … (kısaltıldı; toplam {len(prompt)} karakter)"
    quoted = "\n".join("> " + line if line else ">" for line in body.splitlines())

    now = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M")
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
    target = root / "docs" / "kayit" / "inputlar.md"
    if not target.exists():
        return
    with open(target, "a", encoding="utf-8") as f:
        f.write(f"\n## {now} — {title}\n\n{quoted}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # pylint: disable=broad-except
        pass  # kayıt hatası kullanıcının mesajını asla engellememeli
