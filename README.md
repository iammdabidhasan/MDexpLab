# GhostLock 2.0

GhostLock is a Windows desktop soft-lock utility created by **MD ABID HASAN** and published under **MDexpLab**. It adds a transparent privacy layer over the desktop with a small floating control button, password unlock, emergency password unlock, and security-question recovery.

GhostLock is open source. Everyone is welcome to inspect it, use it, improve it, and contribute fixes or features that make the tool more useful for the community.

## What Is New In 2.0

- Single-click the floating GhostLock icon to open the options panel.
- Floating icon now uses the GhostLock artwork from `assets/ghostlock.ico` / `assets/ghostlock.png`.
- Cleaner first-run setup and installer screens.
- More stable transparent lock overlay with a fixed password panel to avoid flicker.
- Packaged builds now include runtime assets so the exe and source build look consistent.
- Updated project README, ownership notes, and contributor-friendly structure.

## Features

- First-run setup for main password, emergency password, security question, and recovery answer.
- Floating desktop control panel with Lock Now, Change Password, Settings, About & Safety, and Exit.
- Full virtual-desktop transparent overlay for Windows 10/11.
- Password capsule accepts the main password or emergency password.
- Recovery is available while locked with `F1`, `Ctrl+R`, or right-click on the password panel.
- Optional Windows startup shortcut.
- Desktop, Start Menu, and uninstall shortcuts created by `Setup.exe` when Windows allows it.
- Passwords and recovery answers are stored as salted PBKDF2 hashes in `%APPDATA%\GhostLock\config.json`.

## Important Safety Note

GhostLock is a soft privacy guard for moments like downloads, rendering, short breaks, or keeping casual eyes away from a running session. It is not a replacement for Windows Lock, BitLocker, Windows account passwords, endpoint security, or administrator policies.

Windows safety paths such as `Ctrl+Alt+Del`, UAC, restart, sign-out, and administrator-level tools remain outside GhostLock by design.

## Install

1. Open the release folder.
2. Run `Setup.exe`.
3. Leave **Open password setup after installation** enabled if you want to create or replace setup immediately.
4. Create your main password, emergency password, security question, and answer.
5. Click the floating GhostLock icon to open the options panel.
6. Choose **Lock Now** when you want to activate the transparent lock layer.

The installed app is copied to:

```text
%LOCALAPPDATA%\GhostLock\GhostLock.exe
```

## First Safe Test

1. Close or hide anything sensitive before testing.
2. Launch GhostLock.
3. Click the floating icon once and choose **Lock Now**.
4. The first lock test auto-releases after 25 seconds until you successfully unlock once.
5. Type your main password or emergency password and press `Enter`.

Hard emergency exit: press `Ctrl+Alt+Del`, then choose sign out or restart from the Windows secure screen.

## Run From Source

Requirements:

- Windows 10 or Windows 11
- Python 3
- Tkinter, included with standard Python on Windows

```powershell
py ghostlock.py
```

## Build

Install PyInstaller if needed:

```powershell
.\build.ps1 -InstallPyInstaller
```

Build the app and setup executables:

```powershell
.\build.ps1
```

Build only the transferable setup executable:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1 -SetupOnly
```

Build output:

```text
dist\GhostLock.exe
dist\Setup.exe
```

## Uninstall

Use the **GhostLock Uninstall** shortcut in the Start Menu. The uninstaller removes shortcuts and can optionally delete saved password setup and settings.

To manually reset first-run setup, close GhostLock and delete:

```text
%APPDATA%\GhostLock\config.json
```

## Project Structure

```text
ghostlock.py              Main application, installer, uninstaller, and lock overlay
assets/ghostlock.ico      Windows icon
assets/ghostlock.png      Runtime floating icon artwork
assets/version_info.txt   Windows executable version metadata
tests/                    Core behavior tests
build.ps1                 PyInstaller build script
*.spec                    PyInstaller spec files
COPYRIGHT.txt             Ownership and attribution note
LICENSE                   Open-source license
```

## Ownership And Terms

- Creator and owner: **MD ABID HASAN**
- Publisher: **MDexpLab**
- Project: **GhostLock**
- Copyright: Copyright (c) 2026 MD ABID HASAN / MDexpLab.
- License: MIT License, unless a future official release states otherwise.

You may use, study, modify, and share GhostLock under the license terms. Please keep the creator and publisher attribution in source distributions. Modified builds should clearly identify what changed and should not be represented as official MDexpLab releases unless approved by the owner.

## Contributing

Contributions are welcome. Useful areas include accessibility, installer polish, Windows edge-case testing, UI refinements, documentation, and security review.

Before opening a pull request:

1. Keep changes focused.
2. Run the tests.
3. Build locally when changing packaging or assets.
4. Update the README when behavior changes.

```powershell
py -m unittest discover -s tests
```

Thank you for helping make GhostLock cleaner, safer, and available for everyone.
