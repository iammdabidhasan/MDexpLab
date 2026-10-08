GhostLock 2.0 Release Folder
============================

Publisher: MDexpLab
Creator and owner: MD ABID HASAN
License: MIT License

Run:

Setup.exe

What Setup.exe does:

1. Copies GhostLock to the current user's local app folder:
   %LOCALAPPDATA%\GhostLock\GhostLock.exe
2. Creates Desktop, Start Menu, and uninstall shortcuts when Windows allows it.
3. Optionally creates a Windows startup shortcut.
4. Opens the password setup panel so the user can create a password,
   emergency password, security question, and recovery answer.

Python is not required on the receiving computer. Setup.exe includes the runtime.

Quick use:

1. Click the floating GhostLock icon once to open the options panel.
2. Choose Lock Now.
3. Type your main password or emergency password and press Enter to unlock.

Safety notes:

- GhostLock is a transparent soft-lock guard, not a replacement for the Windows
  account lock screen or full-device security.
- The first lock after setup auto-releases after 25 seconds until the user
  successfully unlocks once.
- Emergency escape remains available through Ctrl+Alt+Del.
- Recovery is available from the lock panel with F1, Ctrl+R, or right-click.

To uninstall:

Use the GhostLock Uninstall shortcut in the Start Menu. Exit the floating
widget first for a complete uninstall.

To reset setup for a user:

Delete:
%APPDATA%\GhostLock\config.json

Then launch GhostLock again.
