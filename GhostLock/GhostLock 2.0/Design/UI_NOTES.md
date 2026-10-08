# GhostLock 2.0 UI Notes

## Floating Widget

- The floating widget uses `assets/ghostlock.png` for the visible artwork and `assets/ghostlock.ico` for Windows executable and window identity.
- The desktop widget intentionally draws no extra ring, dot, border, or circular chrome around the icon.
- A single click opens the options panel.
- Dragging starts only after intentional pointer movement, which prevents tiny hand movement from being misread as a drag.
- Double-click remains available as a quick Lock Now shortcut.

## Lock Overlay

- The transparent full-screen overlay remains configurable through Settings.
- The password panel now has a fixed height so status messages do not resize the window.
- The panel alpha changes gently after idle time instead of aggressively fading the password box.
- The status line is always reserved, which keeps the layout stable and reduces flicker.

## Setup And Installer

- Setup is grouped into unlock credentials and account recovery.
- Setup and Settings use scrollable bodies so critical controls remain reachable in smaller windows.
- Installer text clearly explains what files and shortcuts are created.
- Both screens use the GhostLock icon and the same color system as the app.
