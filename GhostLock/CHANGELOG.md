# Changelog

## 2.1.0
**Design**
- New backgroundless ghost logo ("ghost fading into data"), crisp at every size.
- Lock screen shows only a transparent password capsule (no logo, no blur). Messages appear inside it.
- The password capsule fades out completely after inactivity (default 15 s, adjustable) and returns on any mouse move or key press.
- Friendlier setup wizard (welcome, password, backup password, recovery question) and tabbed Settings.
- Dark, consistent UI with DPI-aware sizing.

**Features**
- Double-click the ghost to lock instantly (can be turned off).
- Uninstall from the ghost menu (password required), Settings > Apps, or the Start Menu.
- Start with Windows now uses the per-user Run registry key.

**Security and fixes**
- Escalating cool-down after repeated wrong passwords or recovery answers.
- Recovery now lets you set a new password without the old one.
- Re-running `--setup` on an existing install asks for your password first.
- Alt+F4 can no longer close the lock screen; the floating button is hidden while locked.
- Settings save all-or-nothing; corrupt config is moved aside instead of overwritten.
- Errors are logged to `%APPDATA%\GhostLock\ghostlock.log`.

## 2.0.0
- Single-click floating icon, transparent lock overlay, installer and recovery.
