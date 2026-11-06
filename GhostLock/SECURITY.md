# Security

GhostLock is a **soft privacy screen**, not a security product. It does not replace Windows Lock, BitLocker or account passwords. Known limits: Task Manager (via `Ctrl+Alt+Del`), UAC prompts, restart and sign-out remain available while locked, and a process running as the same user can end GhostLock.

## Reporting a vulnerability
Please use **GitHub > Security > Report a vulnerability** (private reporting) on this repository instead of opening a public issue. Include the Windows version, GhostLock version, and steps to reproduce.

## What is stored
Only `%APPDATA%\GhostLock\config.json` (salted PBKDF2-SHA256 hashes of your passwords and recovery answer, plus your settings) and an error log. GhostLock collects nothing and makes no network connections.
