#!/usr/bin/env python3
"""Alt agent PreToolUse bekçisi.

Kullanım (agent frontmatter'ında):  python3 .claude/hooks/guard.py <rol>

- Edit/Write/NotebookEdit: yalnızca roles.json'daki izinli yollara (veya /tmp altına).
- Read: .env dosyaları engellenir.
- Bash: git push / merge / reset --hard / branch -D, pip/uv install, rm -rf,
  .env okuma ve (gh_write=false rollerde) gh yazma komutları engellenir.

Reddederken PreToolUse JSON'u ile gerekçe döner; izin verirken sessizce çıkar
(normal izin akışı devam eder).
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

BASH_DENY: list[tuple[str, str]] = [
    (r"\bgit\s+push\b", "git push yalnızca orkestratörün işi."),
    (r"\bgit\s+merge\b", "Birleştirme orkestratörün işi (kullanıcı onayıyla)."),
    (r"\bgit\s+rebase\b", "Rebase orkestratörün işi."),
    (r"\bgit\s+reset\s+--hard\b", "reset --hard yasak; değişiklik kaybettirir."),
    (r"\bgit\s+branch\s+-D\b", "Dal silme yasak."),
    (r"\bgit\s+(checkout|switch)\s+(main|master)\b", "main dalına geçme; kendi dalında/worktree'nde kal."),
    (r"\b(pip3?|uv\s+pip|uv)\s+(install|add)\b", "Paket kurulumu yasak; gerekiyorsa orkestratöre bildir."),
    (r"\bpython3?\s+-m\s+pip\s+install\b", "Paket kurulumu yasak; gerekiyorsa orkestratöre bildir."),
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f|\brm\s+-[a-zA-Z]*f[a-zA-Z]*r", "rm -rf yasak."),
    (r"(^|[\s/'\"=])\.env(\.[\w-]+)?(\s|$|['\"])", ".env gizli bilgi içerir; okunamaz."),
]
GH_WRITE = re.compile(
    r"\bgh\s+(issue\s+(create|comment|edit|close|reopen|delete)|"
    r"pr\s+(create|comment|edit|merge|close|review)|label\s+|project\s+|api\s+.*-X\s*(POST|PATCH|PUT|DELETE))"
)


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[guard] {reason}",
        }
    }, ensure_ascii=False))
    sys.exit(0)


def repo_root(cwd: str) -> Path:
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return Path(out.stdout.strip())
    except Exception:  # pylint: disable=broad-except
        return Path(cwd)


def main() -> None:
    role = sys.argv[1] if len(sys.argv) > 1 else ""
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    tin = data.get("tool_input", {}) or {}
    cwd = data.get("cwd") or os.getcwd()

    roles = json.loads((HERE / "roles.json").read_text(encoding="utf-8"))["roles"]
    if role not in roles:
        deny(f"Bilinmeyen rol '{role}'.")
    cfg = roles[role]

    if tool == "Read":
        name = Path(tin.get("file_path", "")).name
        if name == ".env" or name.startswith(".env."):
            deny(".env gizli bilgi içerir; okunamaz.")
        return

    if tool in ("Edit", "Write", "NotebookEdit"):
        raw = tin.get("file_path") or tin.get("notebook_path") or ""
        path = Path(raw)
        if not path.is_absolute():
            path = Path(cwd) / path
        path = path.resolve()
        if str(path).startswith("/tmp/"):
            return
        root = repo_root(cwd).resolve()
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            deny(f"{path} çalışma ağacının ({root}) dışında.")
        if rel.startswith(".claude/") or rel == "CLAUDE.md":
            deny("Agent ayarları/CLAUDE.md yalnızca kullanıcı onayıyla orkestratör tarafından değişir.")
        for pat in cfg["write"]:
            if fnmatch.fnmatch(rel, pat):
                return
        deny(
            f"'{role}' rolü '{rel}' yoluna yazamaz. İzinli: {', '.join(cfg['write'])}. "
            "Bu dosyanın değişmesi gerekiyorsa sahibi olan agente SendMessage ile danış "
            "veya orkestratöre bildir."
        )

    if tool == "Bash":
        cmd = tin.get("command", "")
        for pat, reason in BASH_DENY:
            if re.search(pat, cmd):
                deny(reason)
        if not cfg.get("gh_write") and GH_WRITE.search(cmd):
            deny("GitHub'a yazma (issue/PR/yorum) katip veya orkestratörün işi; bulguyu raporuna ekle.")
        return


if __name__ == "__main__":
    main()
