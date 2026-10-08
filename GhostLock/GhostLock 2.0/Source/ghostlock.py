import base64
import ctypes
import hashlib
import hmac
import json
import os
import platform
import secrets
import shutil
import subprocess
import sys
import time
import traceback
from ctypes import wintypes
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


APP_NAME = "GhostLock"
APP_VERSION = "2.0.0"
APP_PUBLISHER = "MDexpLab"
APP_AUTHOR = "MD ABID HASAN"
APP_COPYRIGHT = "Copyright (c) 2026 MD ABID HASAN / MDexpLab. Open-source software."
CONFIG_VERSION = 2
PBKDF2_ITERATIONS = 260_000
INSTALL_DIR_NAME = APP_NAME
INSTALLED_EXE_NAME = f"{APP_NAME}.exe"
STARTUP_SHORTCUT_NAME = f"{APP_NAME}.lnk"
SINGLE_INSTANCE_MUTEX_NAME = "Local\\GhostLockSingleInstance"
_SINGLE_INSTANCE_MUTEX = None

COLORS = {
    "bg": "#0b1118",
    "surface": "#121b26",
    "surface_2": "#172331",
    "surface_3": "#1e2c3b",
    "text": "#f4f7fb",
    "muted": "#9fb0c1",
    "accent": "#3dd6a3",
    "accent_dark": "#1d9f78",
    "danger": "#ff6b73",
    "warning": "#f4ba59",
}


def enable_dpi_awareness():
    if platform.system() != "Windows":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def app_data_dir():
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def install_dir():
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / INSTALL_DIR_NAME
    return Path.home() / "AppData" / "Local" / INSTALL_DIR_NAME


def desktop_dir():
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def start_menu_dir():
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def startup_dir():
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def startup_shortcut_path():
    return startup_dir() / STARTUP_SHORTCUT_NAME


def current_executable_path():
    source = sys.executable if getattr(sys, "frozen", False) else __file__
    return Path(source).resolve()


def resource_path(*parts):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def asset_path(name):
    return resource_path("assets", name)


def set_window_icon(window):
    try:
        icon = asset_path("ghostlock.ico")
        if icon.exists():
            window.iconbitmap(str(icon))
    except Exception:
        pass


def app_launcher_path():
    installed = install_dir() / INSTALLED_EXE_NAME
    if installed.exists():
        return installed
    return current_executable_path()


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def create_shortcut(link_path, target_path, description=APP_NAME, arguments=""):
    if platform.system() != "Windows":
        return False
    try:
        link_path = Path(link_path)
        target_path = Path(target_path)
        link_path.parent.mkdir(parents=True, exist_ok=True)
        script = (
            "$shell = New-Object -ComObject WScript.Shell; "
            f"$shortcut = $shell.CreateShortcut({ps_quote(link_path)}); "
            f"$shortcut.TargetPath = {ps_quote(target_path)}; "
            f"$shortcut.WorkingDirectory = {ps_quote(target_path.parent)}; "
            f"$shortcut.IconLocation = {ps_quote(target_path)}; "
            f"$shortcut.Description = {ps_quote(description)}; "
            f"$shortcut.Arguments = {ps_quote(arguments)}; "
            "$shortcut.Save()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except Exception:
        return False


def set_start_with_windows(enabled, target_path=None):
    shortcut = startup_shortcut_path()
    if enabled:
        return create_shortcut(
            shortcut,
            target_path or app_launcher_path(),
            f"Start {APP_NAME} by {APP_PUBLISHER} with Windows",
            "--run",
        )
    try:
        if shortcut.exists():
            shortcut.unlink()
        return True
    except Exception:
        return False


def is_start_with_windows():
    return startup_shortcut_path().exists()


def remove_known_shortcuts():
    for path in (
        desktop_dir() / f"{APP_NAME}.lnk",
        start_menu_dir() / f"{APP_NAME}.lnk",
        start_menu_dir() / f"{APP_NAME} Uninstall.lnk",
        startup_shortcut_path(),
    ):
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass


def is_setup_invocation():
    args = {arg.lower() for arg in sys.argv[1:]}
    if "--uninstall" in args:
        return False
    if "--run" in args:
        return False
    if "--install" in args:
        return True
    executable = Path(sys.executable if getattr(sys, "frozen", False) else sys.argv[0])
    stem = executable.stem.lower().replace("_", "").replace("-", "")
    return getattr(sys, "frozen", False) and stem in {"setup", "ghostlocksetup"}


def is_uninstall_invocation():
    return "--uninstall" in {arg.lower() for arg in sys.argv[1:]}


def is_forced_setup_invocation():
    return "--setup" in {arg.lower() for arg in sys.argv[1:]}


def acquire_single_instance():
    global _SINGLE_INSTANCE_MUTEX
    if platform.system() != "Windows":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.GetLastError.argtypes = ()
        kernel32.GetLastError.restype = wintypes.DWORD
        mutex = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX_NAME)
        _SINGLE_INSTANCE_MUTEX = mutex
        return kernel32.GetLastError() != 183
    except Exception:
        return True


def is_another_instance_running():
    if platform.system() != "Windows":
        return False
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.GetLastError.argtypes = ()
        kernel32.GetLastError.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        mutex = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX_NAME)
        already_running = kernel32.GetLastError() == 183
        if mutex:
            kernel32.CloseHandle(mutex)
        return already_running
    except Exception:
        return False


def log_exception(context, exc):
    try:
        path = app_data_dir() / "ghostlock.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {context}\n")
            handle.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        return path
    except Exception:
        return None


def b64encode(raw):
    return base64.b64encode(raw).decode("ascii")


def b64decode(value):
    return base64.b64decode(value.encode("ascii"))


def hash_secret(secret, salt=None, iterations=PBKDF2_ITERATIONS):
    if not isinstance(secret, str) or not secret:
        raise ValueError("Secret must be a non-empty string.")
    raw_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        raw_salt,
        iterations,
    )
    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": iterations,
        "salt": b64encode(raw_salt),
        "hash": b64encode(digest),
    }


def verify_secret(secret, record):
    if not secret or not isinstance(record, dict):
        return False
    try:
        iterations = int(record.get("iterations", PBKDF2_ITERATIONS))
        salt = b64decode(record["salt"])
        expected = b64decode(record["hash"])
    except Exception:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


class ConfigManager:
    def __init__(self):
        self.path = app_data_dir() / "config.json"
        self.data = {}
        self.load()

    def load(self):
        if not self.path.exists():
            self.data = {}
            return
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            self._apply_defaults()
        except Exception:
            self.data = {}

    def _apply_defaults(self):
        if not isinstance(self.data, dict) or not self.data:
            return
        self.data.setdefault("version", CONFIG_VERSION)
        self.data.setdefault("lock_opacity", 0.68)
        self.data.setdefault("first_lock_tested", False)
        self.data.setdefault("start_with_windows", is_start_with_windows())
        self.data.setdefault("widget", {})

    @property
    def is_configured(self):
        return all(
            key in self.data
            for key in (
                "password",
                "emergency_password",
                "security_question",
                "security_answer",
            )
        )

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = int(time.time())
        temp_path = self.path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        os.replace(temp_path, self.path)

    def configure(self, password, emergency_password, question, answer):
        now = int(time.time())
        self.data = {
            "version": CONFIG_VERSION,
            "created_at": now,
            "updated_at": now,
            "password": hash_secret(password),
            "emergency_password": hash_secret(emergency_password),
            "security_question": question.strip(),
            "security_answer": hash_secret(answer.strip().lower()),
            "lock_opacity": 0.68,
            "first_lock_tested": False,
            "start_with_windows": is_start_with_windows(),
            "widget": {},
        }
        self.save()

    def verify_password(self, value):
        return verify_secret(value, self.data.get("password"))

    def verify_emergency_password(self, value):
        return verify_secret(value, self.data.get("emergency_password"))

    def verify_any_unlock_secret(self, value):
        return self.verify_password(value) or self.verify_emergency_password(value)

    def verify_security_answer(self, value):
        return verify_secret(value.strip().lower(), self.data.get("security_answer"))

    def set_password(self, password):
        self.data["password"] = hash_secret(password)
        self.save()

    def set_emergency_password(self, password):
        self.data["emergency_password"] = hash_secret(password)
        self.save()

    def set_security_question(self, question, answer):
        self.data["security_question"] = question.strip()
        self.data["security_answer"] = hash_secret(answer.strip().lower())
        self.save()

    def set_lock_opacity(self, opacity):
        self.data["lock_opacity"] = max(0.35, min(0.9, float(opacity)))
        self.save()

    def mark_first_lock_tested(self):
        self.data["first_lock_tested"] = True
        self.save()

    def set_start_with_windows(self, enabled):
        self.data["start_with_windows"] = bool(enabled)
        self.save()

    def set_widget_position(self, x, y):
        self.data.setdefault("widget", {})
        self.data["widget"]["x"] = int(x)
        self.data["widget"]["y"] = int(y)
        self.save()


def geometry_string(width, height, x, y):
    return f"{int(width)}x{int(height)}{int(x):+d}{int(y):+d}"


def get_virtual_screen_geometry(root):
    if platform.system() == "Windows":
        try:
            user32 = ctypes.windll.user32
            x = user32.GetSystemMetrics(76)
            y = user32.GetSystemMetrics(77)
            width = user32.GetSystemMetrics(78)
            height = user32.GetSystemMetrics(79)
            if width > 0 and height > 0:
                return x, y, width, height
        except Exception:
            pass
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def center_window(window, width, height, reference=None, y_bias=0.5):
    window.update_idletasks()
    if reference:
        reference.update_idletasks()
        rx = reference.winfo_rootx()
        ry = reference.winfo_rooty()
        rw = max(1, reference.winfo_width())
        rh = max(1, reference.winfo_height())
        x = rx + (rw - width) // 2
        y = ry + int((rh - height) * y_bias)
    else:
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
    window.geometry(geometry_string(width, height, x, y))


def apply_round_corners(window, radius=24):
    if platform.system() != "Windows":
        return
    try:
        window.update_idletasks()
        width = max(1, window.winfo_width())
        height = max(1, window.winfo_height())
        hwnd = window.winfo_id()
        region = ctypes.windll.gdi32.CreateRoundRectRgn(
            0,
            0,
            width + 1,
            height + 1,
            radius,
            radius,
        )
        result = ctypes.windll.user32.SetWindowRgn(hwnd, region, True)
        if result == 0:
            ctypes.windll.gdi32.DeleteObject(region)
    except Exception:
        pass


def keep_rounded(window, radius=24):
    def update(_event=None):
        window.after_idle(lambda: apply_round_corners(window, radius))

    window.bind("<Configure>", update, add="+")
    window.after(50, update)


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip = tk.Toplevel(self.widget)
        self.tip.overrideredirect(True)
        self.tip.attributes("-topmost", True)
        self.tip.configure(bg=COLORS["surface_3"])
        label = tk.Label(
            self.tip,
            text=self.text,
            bg=COLORS["surface_3"],
            fg=COLORS["text"],
            padx=10,
            pady=6,
            font=("Segoe UI", 9),
        )
        label.pack()
        self.tip.geometry(f"+{x}+{y}")
        keep_rounded(self.tip, 12)

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class VerticalScrolledFrame:
    def __init__(self, parent, bg):
        self.container = tk.Frame(parent, bg=bg)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self.container,
            bg=bg,
            highlightthickness=0,
            bd=0,
            yscrollincrement=24,
        )
        self.scrollbar = ttk.Scrollbar(
            self.container,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.inner = tk.Frame(self.canvas, bg=bg)
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._update_scroll_region, add="+")
        self.canvas.bind("<Configure>", self._resize_inner, add="+")
        self.canvas.bind("<Enter>", self._bind_mousewheel, add="+")
        self.canvas.bind("<Leave>", self._unbind_mousewheel, add="+")

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event):
        self.canvas.itemconfigure(self.inner_id, width=event.width)

    def _bind_mousewheel(self, _event=None):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event=None):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"


class GhostLockApp:
    def __init__(self, force_setup=False):
        enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.configure(bg=COLORS["bg"])
        set_window_icon(self.root)
        self.config = ConfigManager()
        self.widget = None
        self.lock_overlay = None
        self._configure_style()

        if self.config.is_configured and not force_setup:
            self.root.withdraw()
            self.show_widget()
        else:
            SetupWindow(self.root, self.config, self.show_widget)

    def _configure_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Ghost.TButton",
            background=COLORS["accent_dark"],
            foreground=COLORS["text"],
            borderwidth=0,
            focusthickness=0,
            padding=(16, 10),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", COLORS["accent"]), ("disabled", COLORS["surface_3"])],
            foreground=[("disabled", COLORS["muted"])],
        )
        style.configure(
            "Ghost.Secondary.TButton",
            background=COLORS["surface_3"],
            foreground=COLORS["text"],
            borderwidth=0,
            focusthickness=0,
            padding=(14, 9),
            font=("Segoe UI", 10),
        )
        style.map(
            "Ghost.Secondary.TButton",
            background=[("active", COLORS["surface_2"])],
        )
        style.configure(
            "Ghost.Horizontal.TScale",
            background=COLORS["surface"],
            troughcolor=COLORS["surface_3"],
            sliderthickness=18,
        )

    def show_widget(self):
        if not self.config.is_configured:
            return
        self.root.withdraw()
        if not self.widget:
            self.widget = FloatingWidget(self.root, self.config, self)

    def lock_now(self):
        if self.lock_overlay and self.lock_overlay.active:
            self.lock_overlay.focus()
            return
        try:
            self.lock_overlay = LockOverlay(
                self.root,
                self.config,
                on_unlock=lambda: setattr(self, "lock_overlay", None),
            )
        except Exception as exc:
            self.lock_overlay = None
            log_path = log_exception("Lock Now failed", exc)
            detail = f"\n\nLog: {log_path}" if log_path else ""
            messagebox.showerror(APP_NAME, f"GhostLock could not start the lock overlay.\n\n{exc}{detail}")

    def run(self):
        self.root.mainloop()


class SetupWindow:
    def __init__(self, root, config, on_complete):
        self.root = root
        self.config = config
        self.on_complete = on_complete
        self.password = tk.StringVar()
        self.confirm_password = tk.StringVar()
        self.emergency = tk.StringVar()
        self.confirm_emergency = tk.StringVar()
        self.question = tk.StringVar()
        self.answer = tk.StringVar()
        self.status = tk.StringVar(value="")

        root.deiconify()
        root.title("GhostLock Setup")
        set_window_icon(root)
        root.minsize(560, 420)
        center_window(root, 840, 700)
        self._build()

    def _build(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        outer = tk.Frame(self.root, bg=COLORS["bg"])
        outer.grid(row=0, column=0, sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        header = tk.Frame(outer, bg=COLORS["bg"])
        header.grid(row=0, column=0, sticky="ew", padx=36, pady=(30, 8))
        header.grid_columnconfigure(1, weight=1)

        try:
            icon = tk.PhotoImage(master=self.root, file=str(asset_path("ghostlock.png"))).subsample(8, 8)
            self._setup_icon = icon
            tk.Label(header, image=icon, bg=COLORS["bg"]).grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 14))
        except Exception:
            tk.Label(
                header,
                text="GL",
                bg=COLORS["surface_2"],
                fg=COLORS["accent"],
                font=("Segoe UI", 13, "bold"),
                width=4,
                height=2,
            ).grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 14))

        tk.Label(
            header,
            text="Set up GhostLock",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 28, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")
        tk.Label(
            header,
            text=f"Version {APP_VERSION} | Transparent desktop guard by {APP_PUBLISHER}.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 11),
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", pady=(4, 0))

        scroller = VerticalScrolledFrame(outer, COLORS["bg"])
        scroller.container.grid(row=1, column=0, sticky="nsew")
        scroller.inner.grid_columnconfigure(0, weight=1)

        form = tk.Frame(scroller.inner, bg=COLORS["surface"], padx=30, pady=26)
        form.grid(row=0, column=0, sticky="nsew", padx=36, pady=(18, 28))
        form.grid_columnconfigure(1, weight=1)

        tk.Label(
            form,
            text="Unlock credentials",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        tk.Label(
            form,
            text="Use a main password for daily unlocks and a separate emergency password for recovery.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=690,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        rows = [
            ("Password", self.password, True, 2),
            ("Confirm password", self.confirm_password, True, 3),
            ("Emergency password", self.emergency, True, 4),
            ("Confirm emergency", self.confirm_emergency, True, 5),
        ]
        for label, variable, secret, row in rows:
            tk.Label(
                form,
                text=label,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(0, 18), pady=8)
            entry = tk.Entry(
                form,
                textvariable=variable,
                show="*" if secret else "",
                bg=COLORS["surface_2"],
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="flat",
                highlightthickness=1,
                highlightbackground=COLORS["surface_3"],
                highlightcolor=COLORS["accent"],
                font=("Segoe UI", 11),
            )
            entry.grid(
                row=row,
                column=1,
                sticky="ew",
                pady=8,
                ipady=8,
            )

        tk.Label(
            form,
            text="Account recovery",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        ).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(22, 4))
        tk.Label(
            form,
            text="The answer is stored as a salted hash. Choose a question only you can answer.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=690,
        ).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        for label, variable, secret, row in (
            ("Security question", self.question, False, 8),
            ("Security answer", self.answer, True, 9),
        ):
            tk.Label(
                form,
                text=label,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(0, 18), pady=8)
            tk.Entry(
                form,
                textvariable=variable,
                show="*" if secret else "",
                bg=COLORS["surface_2"],
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="flat",
                highlightthickness=1,
                highlightbackground=COLORS["surface_3"],
                highlightcolor=COLORS["accent"],
                font=("Segoe UI", 11),
            ).grid(row=row, column=1, sticky="ew", pady=8, ipady=8)

        footer = tk.Frame(form, bg=COLORS["surface"])
        footer.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(24, 0))
        footer.grid_columnconfigure(0, weight=1)

        tk.Label(
            footer,
            textvariable=self.status,
            bg=COLORS["surface"],
            fg=COLORS["danger"],
            font=("Segoe UI", 10),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 16))
        setup_button = ttk.Button(
            footer,
            text="Finish Setup",
            style="Ghost.TButton",
            command=self._finish,
        )
        setup_button.grid(row=0, column=1, sticky="e")
        ToolTip(setup_button, "Save your unlock and recovery settings.")

    def _finish(self):
        password = self.password.get()
        confirm_password = self.confirm_password.get()
        emergency = self.emergency.get()
        confirm_emergency = self.confirm_emergency.get()
        question = self.question.get().strip()
        answer = self.answer.get().strip()

        error = self._validate(password, confirm_password, emergency, confirm_emergency, question, answer)
        if error:
            self.status.set(error)
            return
        try:
            self.config.configure(password, emergency, question, answer)
        except Exception as exc:
            self.status.set(f"Could not save setup: {exc}")
            return
        self.status.set("")
        messagebox.showinfo(APP_NAME, "Setup complete. The floating widget is ready.")
        self.on_complete()

    @staticmethod
    def _validate(password, confirm_password, emergency, confirm_emergency, question, answer):
        if len(password) < 6:
            return "Use a password with at least 6 characters."
        if password != confirm_password:
            return "Password confirmation does not match."
        if len(emergency) < 6:
            return "Use an emergency password with at least 6 characters."
        if emergency != confirm_emergency:
            return "Emergency confirmation does not match."
        if emergency == password:
            return "Emergency password must be different from the main password."
        if len(question) < 6:
            return "Write a security question you will recognize later."
        if len(answer) < 2:
            return "Security answer must be at least 2 characters."
        return ""


class FloatingWidget:
    def __init__(self, root, config, app):
        self.root = root
        self.config = config
        self.app = app
        self.size = 64
        self.transparent_color = "#010203"
        self.drag_threshold = 9
        self.drag_start = None
        self.dragged = False
        self.menu = None
        self.icon_image = None
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=self.transparent_color)
        try:
            self.window.attributes("-transparentcolor", self.transparent_color)
        except tk.TclError:
            pass
        self.window.resizable(False, False)
        self._place_initially()
        self._build()

    def _place_initially(self):
        widget = self.config.data.get("widget", {})
        x = widget.get("x")
        y = widget.get("y")
        if x is None or y is None:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = max(16, screen_w - self.size - 34)
            y = max(16, screen_h - self.size - 88)
        self.window.geometry(geometry_string(self.size, self.size, x, y))

    def _build(self):
        canvas = tk.Canvas(
            self.window,
            width=self.size,
            height=self.size,
            bg=self.transparent_color,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(fill="both", expand=True)
        try:
            image = tk.PhotoImage(master=self.window, file=str(asset_path("ghostlock.png")))
            factor = max(1, int(round(image.width() / self.size)))
            self.icon_image = image.subsample(factor, factor)
            canvas.create_image(self.size // 2, self.size // 2, image=self.icon_image)
        except Exception:
            canvas.create_text(
                self.size // 2,
                self.size // 2 - 2,
                text="GL",
                fill=COLORS["text"],
                font=("Segoe UI", 16, "bold"),
            )
        for widget in (self.window, canvas):
            widget.bind("<ButtonPress-1>", self._start_drag, add="+")
            widget.bind("<B1-Motion>", self._drag, add="+")
            widget.bind("<ButtonRelease-1>", self._release, add="+")
            widget.bind("<Double-Button-1>", self._lock_now, add="+")
            widget.bind("<Button-3>", self._toggle_menu, add="+")
        ToolTip(canvas, "GhostLock")

    def _start_drag(self, event):
        self.drag_start = (
            event.x_root,
            event.y_root,
            self.window.winfo_x(),
            self.window.winfo_y(),
        )
        self.dragged = False
        return "break"

    def _drag(self, event):
        if not self.drag_start:
            return
        start_x, start_y, win_x, win_y = self.drag_start
        dx = event.x_root - start_x
        dy = event.y_root - start_y
        if not self.dragged and (dx * dx + dy * dy) >= self.drag_threshold * self.drag_threshold:
            self.dragged = True
        if self.dragged:
            self.window.geometry(f"+{win_x + dx}+{win_y + dy}")
            if self.menu:
                self._position_menu()
        return "break"

    def _release(self, _event=None):
        if self.drag_start and self.dragged:
            self.config.set_widget_position(self.window.winfo_x(), self.window.winfo_y())
        elif self.drag_start:
            self._toggle_menu()
        self.drag_start = None
        self.dragged = False
        return "break"

    def _toggle_menu(self, _event=None):
        if self.menu and self.menu.winfo_exists():
            self.menu.destroy()
            self.menu = None
            return "break"
        self.menu = tk.Toplevel(self.window)
        self.menu.overrideredirect(True)
        self.menu.attributes("-topmost", True)
        self.menu.configure(bg=COLORS["surface"])
        keep_rounded(self.menu, 20)

        frame = tk.Frame(self.menu, bg=COLORS["surface"], padx=14, pady=14)
        frame.pack(fill="both", expand=True)

        header = tk.Frame(frame, bg=COLORS["surface"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(1, weight=1)
        tk.Label(
            header,
            text="GhostLock",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="Ready",
            bg=COLORS["surface"],
            fg=COLORS["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="e",
        ).grid(row=0, column=1, sticky="e")

        buttons = [
            ("Lock Now", self._lock_now),
            ("Change Password", self._change_password),
            ("Settings", self._settings),
            ("About & Safety", self._help),
            ("Exit", self._exit),
        ]
        for row, (text, command) in enumerate(buttons):
            style = "Ghost.TButton" if row == 0 else "Ghost.Secondary.TButton"
            button = ttk.Button(frame, text=text, style=style, command=command)
            button.grid(row=row + 1, column=0, sticky="ew", pady=(0 if row == 0 else 8, 8 if row < len(buttons) - 1 else 0))
        frame.grid_columnconfigure(0, weight=1)
        self.menu.geometry("248x302")
        self._position_menu()
        self.menu.bind("<Escape>", lambda _event: self._hide_menu(), add="+")
        self.menu.focus_force()
        return "break"

    def _position_menu(self):
        if not self.menu:
            return
        self.menu.update_idletasks()
        widget_x = self.window.winfo_x()
        widget_y = self.window.winfo_y()
        menu_w = self.menu.winfo_width()
        menu_h = self.menu.winfo_height()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = widget_x - menu_w - 12
        y = widget_y
        if x < 8:
            x = widget_x + self.size + 12
        if y + menu_h > screen_h - 8:
            y = screen_h - menu_h - 8
        if x + menu_w > screen_w - 8:
            x = screen_w - menu_w - 8
        self.menu.geometry(f"+{max(8, x)}+{max(8, y)}")

    def _hide_menu(self):
        if self.menu and self.menu.winfo_exists():
            self.menu.destroy()
        self.menu = None

    def _lock_now(self, _event=None):
        self._hide_menu()
        self.app.lock_now()
        return "break"

    def _change_password(self):
        self._hide_menu()
        ChangePasswordWindow(self.root, self.config)

    def _settings(self):
        self._hide_menu()
        SettingsWindow(self.root, self.config)

    def _help(self):
        self._hide_menu()
        HelpWindow(self.root)

    def _exit(self):
        self._hide_menu()
        self.window.destroy()
        self.root.destroy()


class ModalWindow:
    def __init__(self, root, title, width, height):
        self.root = root
        self.window = tk.Toplevel(root)
        self.window.title(title)
        self.window.configure(bg=COLORS["bg"])
        set_window_icon(self.window)
        self.window.minsize(width, height)
        try:
            if root.winfo_viewable():
                self.window.transient(root)
        except tk.TclError:
            pass
        center_window(self.window, width, height)
        try:
            self.window.attributes("-topmost", True)
            self.window.after(600, lambda: self.window.attributes("-topmost", False))
        except tk.TclError:
            pass
        self.window.lift()
        self.window.focus_force()


class ChangePasswordWindow(ModalWindow):
    def __init__(self, root, config):
        self.config = config
        self.current = tk.StringVar()
        self.new = tk.StringVar()
        self.confirm = tk.StringVar()
        self.status = tk.StringVar()
        super().__init__(root, "Change Password", 480, 360)
        self._build()

    def _build(self):
        frame = tk.Frame(self.window, bg=COLORS["surface"], padx=26, pady=24)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        frame.grid_columnconfigure(1, weight=1)
        tk.Label(frame, text="Change Password", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))
        self._entry(frame, "Current or emergency", self.current, 1)
        self._entry(frame, "New password", self.new, 2)
        self._entry(frame, "Confirm new", self.confirm, 3)
        tk.Label(frame, textvariable=self.status, bg=COLORS["surface"], fg=COLORS["danger"], font=("Segoe UI", 9)).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 12))
        button_row = tk.Frame(frame, bg=COLORS["surface"])
        button_row.grid(row=5, column=0, columnspan=2, sticky="e")
        ttk.Button(button_row, text="Cancel", style="Ghost.Secondary.TButton", command=self.window.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text="Save", style="Ghost.TButton", command=self._save).pack(side="left")

    def _entry(self, parent, label, variable, row):
        tk.Label(parent, text=label, bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=8, padx=(0, 14))
        tk.Entry(parent, textvariable=variable, show="*", bg=COLORS["surface_2"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", font=("Segoe UI", 11)).grid(row=row, column=1, sticky="ew", pady=8, ipady=7)

    def _save(self):
        if not self.config.verify_any_unlock_secret(self.current.get()):
            self.status.set("Current password or emergency password did not match.")
            return
        if len(self.new.get()) < 6:
            self.status.set("New password must be at least 6 characters.")
            return
        if self.new.get() != self.confirm.get():
            self.status.set("New password confirmation does not match.")
            return
        self.config.set_password(self.new.get())
        messagebox.showinfo(APP_NAME, "Password updated.")
        self.window.destroy()


class HelpWindow(ModalWindow):
    def __init__(self, root):
        super().__init__(root, "GhostLock About & Safety", 580, 480)
        self._build()

    def _build(self):
        frame = tk.Frame(self.window, bg=COLORS["surface"], padx=28, pady=24)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        frame.grid_columnconfigure(0, weight=1)

        tk.Label(
            frame,
            text="About & Safety",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 16))

        lines = [
            f"{APP_NAME} {APP_VERSION}",
            f"Publisher: {APP_PUBLISHER}",
            f"Creator: {APP_AUTHOR}",
            APP_COPYRIGHT,
            "Open the panel: single-click the floating GhostLock icon.",
            "Lock: choose Lock Now, or double-click the floating icon for a shortcut.",
            "Unlock: type the main password or emergency password, then press Enter.",
            "Recovery while locked: press F1, Ctrl+R, or right-click the password capsule.",
            "Hard emergency escape: Ctrl+Alt+Del remains available through Windows.",
            f"Settings and logs are stored under: {app_data_dir()}",
        ]
        for row, line in enumerate(lines, start=1):
            tk.Label(
                frame,
                text=line,
                bg=COLORS["surface"],
                fg=COLORS["muted"] if row < len(lines) else COLORS["warning"],
                wraplength=490,
                justify="left",
                anchor="w",
                font=("Segoe UI", 10),
            ).grid(row=row, column=0, sticky="ew", pady=(0, 10))

        ttk.Button(
            frame,
            text="Close",
            style="Ghost.TButton",
            command=self.window.destroy,
        ).grid(row=len(lines) + 1, column=0, sticky="e", pady=(14, 0))


class SettingsWindow(ModalWindow):
    def __init__(self, root, config):
        self.config = config
        self.current = tk.StringVar()
        self.emergency = tk.StringVar()
        self.confirm_emergency = tk.StringVar()
        self.question = tk.StringVar(value=config.data.get("security_question", ""))
        self.answer = tk.StringVar()
        self.opacity = tk.DoubleVar(value=float(config.data.get("lock_opacity", 0.68)) * 100)
        self.start_with_windows = tk.BooleanVar(value=is_start_with_windows())
        self.status = tk.StringVar()
        super().__init__(root, "GhostLock Settings", 600, 440)
        self._build()

    def _build(self):
        scroller = VerticalScrolledFrame(self.window, COLORS["bg"])
        scroller.container.pack(fill="both", expand=True)
        scroller.inner.grid_columnconfigure(0, weight=1)

        outer = tk.Frame(scroller.inner, bg=COLORS["surface"], padx=26, pady=24)
        outer.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        outer.grid_columnconfigure(1, weight=1)
        tk.Label(outer, text="Settings", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))
        self._entry(outer, "Current or emergency", self.current, 1, True)
        self._entry(outer, "New emergency", self.emergency, 2, True)
        self._entry(outer, "Confirm emergency", self.confirm_emergency, 3, True)
        self._entry(outer, "Security question", self.question, 4, False)
        self._entry(outer, "New security answer", self.answer, 5, True)

        tk.Label(outer, text="Overlay opacity", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 10, "bold")).grid(row=6, column=0, sticky="w", pady=(16, 8), padx=(0, 14))
        ttk.Scale(outer, from_=35, to=90, variable=self.opacity, style="Ghost.Horizontal.TScale").grid(row=6, column=1, sticky="ew", pady=(16, 8))

        tk.Label(outer, text="Startup", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 10, "bold")).grid(row=7, column=0, sticky="w", pady=8, padx=(0, 14))
        tk.Checkbutton(
            outer,
            text="Start GhostLock when Windows starts",
            variable=self.start_with_windows,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            activebackground=COLORS["surface"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["surface_2"],
            font=("Segoe UI", 10),
            anchor="w",
        ).grid(row=7, column=1, sticky="ew", pady=8)

        tk.Label(outer, textvariable=self.status, bg=COLORS["surface"], fg=COLORS["danger"], font=("Segoe UI", 9), anchor="w").grid(row=8, column=0, columnspan=2, sticky="ew", pady=(8, 12))
        row = tk.Frame(outer, bg=COLORS["surface"])
        row.grid(row=9, column=0, columnspan=2, sticky="e")
        ttk.Button(row, text="Cancel", style="Ghost.Secondary.TButton", command=self.window.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Save Settings", style="Ghost.TButton", command=self._save).pack(side="left")

    def _entry(self, parent, label, variable, row, secret):
        tk.Label(parent, text=label, bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=8, padx=(0, 14))
        tk.Entry(parent, textvariable=variable, show="*" if secret else "", bg=COLORS["surface_2"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", font=("Segoe UI", 11)).grid(row=row, column=1, sticky="ew", pady=8, ipady=7)

    def _save(self):
        if not self.config.verify_any_unlock_secret(self.current.get()):
            self.status.set("Current password or emergency password did not match.")
            return

        emergency = self.emergency.get()
        confirm = self.confirm_emergency.get()
        if emergency or confirm:
            if len(emergency) < 6:
                self.status.set("Emergency password must be at least 6 characters.")
                return
            if emergency != confirm:
                self.status.set("Emergency password confirmation does not match.")
                return
            self.config.set_emergency_password(emergency)

        question = self.question.get().strip()
        answer = self.answer.get().strip()
        old_question = self.config.data.get("security_question", "")
        if question != old_question or answer:
            if len(question) < 6:
                self.status.set("Write a security question you will recognize later.")
                return
            if len(answer) < 2:
                self.status.set("Enter a new security answer to change recovery settings.")
                return
            self.config.set_security_question(question, answer)

        self.config.set_lock_opacity(self.opacity.get() / 100)
        if not set_start_with_windows(self.start_with_windows.get()):
            self.status.set("Could not update Windows startup shortcut.")
            return
        self.config.set_start_with_windows(self.start_with_windows.get())
        messagebox.showinfo(APP_NAME, "Settings saved.")
        self.window.destroy()


class InstallerWindow:
    def __init__(self, root):
        self.root = root
        self.status = tk.StringVar(value="")
        self.launch_after_install = tk.BooleanVar(value=True)
        self.start_with_windows = tk.BooleanVar(value=False)
        self.root.title("GhostLock Setup")
        self.root.configure(bg=COLORS["bg"])
        set_window_icon(self.root)
        self.root.resizable(True, True)
        self.root.minsize(640, 520)
        center_window(self.root, 760, 580)
        self._configure_style()
        self._build()

    def _configure_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Installer.TButton",
            background=COLORS["accent_dark"],
            foreground=COLORS["text"],
            borderwidth=0,
            focusthickness=0,
            padding=(18, 12),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Installer.TButton", background=[("active", COLORS["accent"])])
        style.configure(
            "Installer.Secondary.TButton",
            background=COLORS["surface_3"],
            foreground=COLORS["text"],
            borderwidth=0,
            focusthickness=0,
            padding=(16, 11),
            font=("Segoe UI", 10),
        )
        style.map("Installer.Secondary.TButton", background=[("active", COLORS["surface_2"])])

    def _build(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        outer = tk.Frame(self.root, bg=COLORS["bg"])
        outer.grid(row=0, column=0, sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        header = tk.Frame(outer, bg=COLORS["bg"])
        header.grid(row=0, column=0, sticky="ew", padx=36, pady=(30, 10))
        header.grid_columnconfigure(1, weight=1)
        try:
            icon = tk.PhotoImage(master=self.root, file=str(asset_path("ghostlock.png"))).subsample(8, 8)
            self._installer_icon = icon
            tk.Label(header, image=icon, bg=COLORS["bg"]).grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 14))
        except Exception:
            tk.Label(
                header,
                text="GL",
                bg=COLORS["surface_2"],
                fg=COLORS["accent"],
                font=("Segoe UI", 13, "bold"),
                width=4,
                height=2,
            ).grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 14))
        tk.Label(
            header,
            text=f"GhostLock {APP_VERSION} Setup",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 26, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")
        tk.Label(
            header,
            text=f"Install the transparent desktop guard by {APP_PUBLISHER} for this Windows user.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 11),
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", pady=(4, 0))

        panel = tk.Frame(outer, bg=COLORS["surface"], padx=28, pady=26)
        panel.grid(row=1, column=0, sticky="nsew", padx=36, pady=(18, 28))
        panel.grid_columnconfigure(0, weight=1)

        install_path = install_dir() / INSTALLED_EXE_NAME
        tk.Label(
            panel,
            text="Install summary",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            justify="left",
            font=("Segoe UI", 15, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            panel,
            text=f"App location:\n{install_path}",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            justify="left",
            font=("Segoe UI", 10),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 16))

        tk.Label(
            panel,
            text="Setup will copy the app, create Desktop and Start Menu shortcuts, and can open the full password setup panel when installation completes.",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            justify="left",
            wraplength=620,
            font=("Segoe UI", 11),
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", pady=(0, 22))

        tk.Checkbutton(
            panel,
            text="Open password setup after installation",
            variable=self.launch_after_install,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            activebackground=COLORS["surface"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["surface_2"],
            font=("Segoe UI", 10),
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", pady=(0, 8))

        tk.Checkbutton(
            panel,
            text="Start GhostLock when Windows starts",
            variable=self.start_with_windows,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            activebackground=COLORS["surface"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["surface_2"],
            font=("Segoe UI", 10),
            anchor="w",
        ).grid(row=4, column=0, sticky="ew", pady=(0, 20))

        tk.Label(
            panel,
            textvariable=self.status,
            bg=COLORS["surface"],
            fg=COLORS["warning"],
            font=("Segoe UI", 9),
            anchor="w",
        ).grid(row=5, column=0, sticky="ew", pady=(0, 16))

        row = tk.Frame(panel, bg=COLORS["surface"])
        row.grid(row=6, column=0, sticky="e")
        ttk.Button(row, text="Close", style="Installer.Secondary.TButton", command=self.root.destroy).pack(side="left", padx=(0, 10))
        ttk.Button(row, text="Install", style="Installer.TButton", command=self._install).pack(side="left")

    def _install(self):
        try:
            if is_another_instance_running():
                self.status.set("GhostLock is already running. Exit the floating widget, then install again.")
                messagebox.showwarning(
                    APP_NAME,
                    "GhostLock is already running.\n\nExit the floating widget first, then run Setup.exe again.",
                )
                return
            self.status.set("Installing...")
            self.root.update_idletasks()
            source = current_executable_path()
            target_dir = install_dir()
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / INSTALLED_EXE_NAME

            if source != target:
                shutil.copy2(source, target)

            create_shortcut(desktop_dir() / f"{APP_NAME}.lnk", target, f"Launch {APP_NAME} by {APP_PUBLISHER}", "--run")
            create_shortcut(start_menu_dir() / f"{APP_NAME}.lnk", target, f"Launch {APP_NAME} by {APP_PUBLISHER}", "--run")
            create_shortcut(start_menu_dir() / f"{APP_NAME} Uninstall.lnk", target, f"Uninstall {APP_NAME}", "--uninstall")
            set_start_with_windows(self.start_with_windows.get(), target)

            info = {
                "installed_at": int(time.time()),
                "source": str(source),
                "target": str(target),
                "version": CONFIG_VERSION,
                "app_version": APP_VERSION,
                "publisher": APP_PUBLISHER,
                "author": APP_AUTHOR,
                "copyright": APP_COPYRIGHT,
                "start_with_windows": bool(self.start_with_windows.get()),
            }
            (target_dir / "install_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

            if self.launch_after_install.get():
                subprocess.Popen(
                    [str(target), "--setup"],
                    cwd=str(target.parent),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                messagebox.showinfo(APP_NAME, "GhostLock is installed. Password setup is opening now.")
            else:
                messagebox.showinfo(APP_NAME, "GhostLock is installed.")
            self.root.destroy()
        except Exception as exc:
            log_path = log_exception("Setup install failed", exc)
            detail = f"\n\nLog: {log_path}" if log_path else ""
            self.status.set("Install failed. Close GhostLock if it is already running, then try again.")
            messagebox.showerror(APP_NAME, f"Setup could not complete.\n\n{exc}{detail}")


class UninstallerWindow:
    def __init__(self, root):
        self.root = root
        self.delete_user_data = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="")
        self.root.title("GhostLock Uninstall")
        self.root.configure(bg=COLORS["bg"])
        set_window_icon(self.root)
        self.root.resizable(True, True)
        self.root.minsize(560, 420)
        center_window(self.root, 640, 460)
        self._configure_style()
        self._build()

    def _configure_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Uninstall.TButton",
            background=COLORS["danger"],
            foreground=COLORS["text"],
            borderwidth=0,
            focusthickness=0,
            padding=(18, 12),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Uninstall.TButton", background=[("active", "#ff858b")])
        style.configure(
            "Uninstall.Secondary.TButton",
            background=COLORS["surface_3"],
            foreground=COLORS["text"],
            borderwidth=0,
            focusthickness=0,
            padding=(16, 11),
            font=("Segoe UI", 10),
        )
        style.map("Uninstall.Secondary.TButton", background=[("active", COLORS["surface_2"])])

    def _build(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        outer = tk.Frame(self.root, bg=COLORS["bg"])
        outer.grid(row=0, column=0, sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        header = tk.Frame(outer, bg=COLORS["bg"])
        header.grid(row=0, column=0, sticky="ew", padx=34, pady=(30, 10))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="Uninstall GhostLock",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 24, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        tk.Label(
            header,
            text=f"Remove {APP_NAME} by {APP_PUBLISHER} from this Windows user account.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 11),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

        panel = tk.Frame(outer, bg=COLORS["surface"], padx=26, pady=24)
        panel.grid(row=1, column=0, sticky="nsew", padx=34, pady=22)
        panel.grid_columnconfigure(0, weight=1)

        tk.Label(
            panel,
            text=f"Installed files:\n{install_dir()}",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            justify="left",
            font=("Segoe UI", 10),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 18))

        tk.Label(
            panel,
            text="Exit the floating widget first for a complete uninstall.",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            justify="left",
            wraplength=520,
            font=("Segoe UI", 11),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 18))

        tk.Checkbutton(
            panel,
            text="Delete saved password setup and settings",
            variable=self.delete_user_data,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            activebackground=COLORS["surface"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["surface_2"],
            font=("Segoe UI", 10),
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", pady=(0, 18))

        tk.Label(
            panel,
            textvariable=self.status,
            bg=COLORS["surface"],
            fg=COLORS["warning"],
            font=("Segoe UI", 9),
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", pady=(0, 16))

        row = tk.Frame(panel, bg=COLORS["surface"])
        row.grid(row=4, column=0, sticky="e")
        ttk.Button(row, text="Cancel", style="Uninstall.Secondary.TButton", command=self.root.destroy).pack(side="left", padx=(0, 10))
        ttk.Button(row, text="Remove", style="Uninstall.TButton", command=self._uninstall).pack(side="left")

    def _uninstall(self):
        if not messagebox.askyesno(APP_NAME, "Remove GhostLock from this user account?"):
            return
        try:
            self.status.set("Removing shortcuts...")
            self.root.update_idletasks()
            remove_known_shortcuts()

            if self.delete_user_data.get():
                self.status.set("Removing saved setup data...")
                self.root.update_idletasks()
                shutil.rmtree(app_data_dir(), ignore_errors=True)

            self._schedule_install_dir_removal()
            messagebox.showinfo(
                APP_NAME,
                "GhostLock uninstall is scheduled. If the floating widget is still open, exit it and run uninstall again to remove remaining files.",
            )
            self.root.destroy()
        except Exception as exc:
            log_path = log_exception("Uninstall failed", exc)
            detail = f"\n\nLog: {log_path}" if log_path else ""
            self.status.set("Uninstall failed.")
            messagebox.showerror(APP_NAME, f"GhostLock could not finish uninstall.\n\n{exc}{detail}")

    def _schedule_install_dir_removal(self):
        target = install_dir().resolve()
        if target.name != INSTALL_DIR_NAME:
            return
        script = (
            "Start-Sleep -Seconds 2; "
            f"Remove-Item -LiteralPath {ps_quote(target)} -Recurse -Force -ErrorAction SilentlyContinue"
        )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


class LockOverlay:
    def __init__(self, root, config, on_unlock):
        self.root = root
        self.config = config
        self.on_unlock = on_unlock
        self.active = True
        self.password = tk.StringVar()
        self.first_lock_test_mode = not bool(config.data.get("first_lock_tested", False))
        self.default_status = "Enter your main or emergency password, then press Enter."
        status_text = "First test lock: auto releases in 25 seconds."
        if not self.first_lock_test_mode:
            status_text = self.default_status
        self.status = tk.StringVar(value=status_text)
        self.safety = tk.StringVar(value="")
        self.test_remaining = 25
        self.visible_alpha = 0.97
        self.idle_alpha = 0.88
        self.panel_alpha = self.visible_alpha
        self.target_alpha = self.visible_alpha
        self.last_activity = time.monotonic()
        self.fade_after_seconds = 10.0
        self.panel_height = 150
        self.compact_panel_height = self.panel_height
        self.expanded_panel_height = self.panel_height
        self.attempts = 0
        self.overlay = None
        self.panel = None
        self.entry = None
        self.forgot = None
        self.recovery_entry = None
        self.status_label = None
        self.safety_label = None
        self._build()

    def _build(self):
        vx, vy, width, height = get_virtual_screen_geometry(self.root)
        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.configure(bg="#02050a")
        self.overlay.attributes("-topmost", True)
        self.overlay.attributes("-alpha", float(self.config.data.get("lock_opacity", 0.68)))
        self.overlay.geometry(geometry_string(width, height, vx, vy))
        self.overlay.bind("<ButtonPress>", self._focus_password, add="+")
        self.overlay.bind("<KeyPress>", self._redirect_key, add="+")
        self.overlay.bind("<Motion>", self._wake_ui, add="+")

        panel_w = min(500, max(380, width // 4))
        panel_h = self.panel_height
        panel_x = vx + (width - panel_w) // 2
        panel_y = vy + int(height * 0.54) - panel_h // 2
        self.panel = tk.Toplevel(self.root)
        self.panel.overrideredirect(True)
        self.panel.configure(bg=COLORS["surface"])
        self.panel.attributes("-topmost", True)
        self.panel.attributes("-alpha", self.panel_alpha)
        self.panel.geometry(geometry_string(panel_w, panel_h, panel_x, panel_y))
        self.panel.bind("<KeyPress>", self._redirect_key, add="+")
        self.panel.bind("<Motion>", self._wake_ui, add="+")
        self.panel.bind("<ButtonPress-1>", self._focus_password, add="+")
        self.panel.bind("<ButtonPress-3>", self._show_forgot, add="+")
        keep_rounded(self.panel, 34)

        frame = tk.Frame(self.panel, bg=COLORS["surface"], padx=22, pady=16)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        frame.bind("<Motion>", self._wake_ui, add="+")
        frame.bind("<ButtonPress-3>", self._show_forgot, add="+")

        header = tk.Frame(frame, bg=COLORS["surface"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="GhostLock is active",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        tk.Label(
            header,
            text="F1 for recovery",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
            anchor="e",
        ).grid(row=0, column=1, sticky="e")

        self.entry = tk.Entry(
            frame,
            textvariable=self.password,
            show="*",
            justify="center",
            bg=COLORS["surface_2"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["surface_3"],
            highlightcolor=COLORS["accent"],
            font=("Segoe UI", 18),
        )
        self.entry.grid(row=1, column=0, sticky="ew", ipady=10)
        self.entry.bind("<KeyPress>", self._entry_keypress, add="+")
        self.entry.bind("<Motion>", self._wake_ui, add="+")
        self.entry.bind("<ButtonPress-3>", self._show_forgot, add="+")

        self.status_label = tk.Label(
            frame,
            textvariable=self.status,
            bg=COLORS["surface"],
            fg=COLORS["warning"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.status_label.grid(row=2, column=0, sticky="ew", pady=(9, 0))
        self.status_label.bind("<Motion>", self._wake_ui, add="+")
        self.status_label.bind("<ButtonPress-3>", self._show_forgot, add="+")
        if not self.first_lock_test_mode:
            self._set_status_visible(False)

        self.focus()
        self._keep_front()
        self._fade_check()
        if self.first_lock_test_mode:
            self._tick_first_lock_test()

    def focus(self):
        if not self.active:
            return
        for window in (self.overlay, self.panel, self.forgot):
            if window and window.winfo_exists():
                window.attributes("-topmost", True)
                window.lift()
        if self.recovery_entry and self.recovery_entry.winfo_exists():
            self.recovery_entry.focus_force()
            self.recovery_entry.icursor("end")
        elif self.entry and self.entry.winfo_exists():
            self.entry.focus_force()
            self.entry.icursor("end")

    def _keep_front(self):
        if not self.active:
            return
        for window in (self.overlay, self.panel, self.forgot):
            if window and window.winfo_exists():
                try:
                    window.attributes("-topmost", True)
                    window.lift()
                except tk.TclError:
                    return
        current_focus = self.root.focus_get()
        expected = [self.entry, self.recovery_entry]
        if current_focus not in expected:
            self.focus()
        self.panel.after(500, self._keep_front)

    def _focus_password(self, _event=None):
        self._wake_ui()
        self.focus()
        return "break"

    def _wake_ui(self, _event=None):
        if not self.active:
            return
        self.last_activity = time.monotonic()
        self._set_target_alpha(self.visible_alpha)

    def _fade_check(self):
        if not self.active:
            return
        if not (self.forgot and self.forgot.winfo_exists()):
            idle_for = time.monotonic() - self.last_activity
            if idle_for >= self.fade_after_seconds:
                self._set_target_alpha(self.idle_alpha)
        self.panel.after(500, self._fade_check)

    def _set_target_alpha(self, alpha):
        next_alpha = max(self.idle_alpha, min(self.visible_alpha, float(alpha)))
        if abs(next_alpha - self.target_alpha) < 0.005 and abs(self.panel_alpha - next_alpha) < 0.005:
            return
        self.target_alpha = next_alpha
        self._animate_panel_alpha()

    def _animate_panel_alpha(self):
        if not self.active or not self.panel or not self.panel.winfo_exists():
            return
        delta = self.target_alpha - self.panel_alpha
        if abs(delta) < 0.025:
            self.panel_alpha = self.target_alpha
        else:
            self.panel_alpha += 0.035 if delta > 0 else -0.025
        try:
            self.panel.attributes("-alpha", self.panel_alpha)
        except tk.TclError:
            return
        if abs(self.target_alpha - self.panel_alpha) >= 0.025:
            self.panel.after(60, self._animate_panel_alpha)

    def _set_status_visible(self, visible):
        if not self.status_label or not self.panel or not self.panel.winfo_exists():
            return
        color = COLORS["warning"] if visible else COLORS["muted"]
        self.status_label.configure(fg=color)

    def _show_status(self, text, clear_after_ms=0):
        self.status.set(text)
        self._set_status_visible(bool(text))
        self._wake_ui()
        if clear_after_ms:
            self.panel.after(clear_after_ms, lambda: self._clear_status(text))

    def _clear_status(self, expected_text=None):
        if not self.active or self.first_lock_test_mode:
            return
        if expected_text is None or self.status.get() == expected_text:
            self.status.set(self.default_status)
            self._set_status_visible(False)

    def _entry_keypress(self, event):
        self._wake_ui()
        if event.keysym == "Return":
            return self._try_unlock()
        if event.keysym == "Escape":
            return self._focus_password()
        if event.keysym == "F1" or (event.keysym.lower() == "r" and (event.state & 0x0004)):
            return self._show_forgot()
        return None

    def _redirect_key(self, event):
        self._wake_ui()
        if event.widget == self.entry:
            return
        if event.keysym == "F1" or (event.keysym.lower() == "r" and (event.state & 0x0004)):
            return self._show_forgot()
        if event.keysym == "Return":
            self._try_unlock()
            return "break"
        if event.keysym == "BackSpace":
            self.password.set(self.password.get()[:-1])
            self.focus()
            return "break"
        if event.keysym == "Escape":
            self.focus()
            return "break"
        if event.char and event.char >= " ":
            self.password.set(self.password.get() + event.char)
            self.focus()
            return "break"
        self.focus()
        return "break"

    def _try_unlock(self):
        value = self.password.get()
        if self.config.verify_any_unlock_secret(value):
            if self.first_lock_test_mode:
                self.config.mark_first_lock_tested()
                self.first_lock_test_mode = False
            self._unlock()
            return "break"
        self.attempts += 1
        self.password.set("")
        status_text = "That password did not match."
        if self.attempts >= 3:
            status_text = "Still locked. Press F1 or right-click for recovery."
        self._show_status(status_text, clear_after_ms=4200)
        self.focus()
        return "break"

    def _tick_first_lock_test(self):
        if not self.active or not self.first_lock_test_mode:
            return
        if self.test_remaining <= 0:
            self._unlock(auto_release=True)
            self.root.after(
                250,
                lambda: messagebox.showinfo(
                    APP_NAME,
                    "The first test lock auto-released. Try Lock Now again after you confirm the password box accepts typing.",
                ),
            )
            return
        self._show_status(f"Safety test mode: auto release in {self.test_remaining}s")
        self.test_remaining -= 1
        self.panel.after(1000, self._tick_first_lock_test)

    def _show_forgot(self, _event=None):
        self._wake_ui()
        if self.forgot and self.forgot.winfo_exists():
            self.forgot.lift()
            if self.recovery_entry and self.recovery_entry.winfo_exists():
                self.recovery_entry.focus_force()
            return "break"
        self.forgot = tk.Toplevel(self.panel)
        self.forgot.overrideredirect(True)
        self.forgot.attributes("-topmost", True)
        self.forgot.configure(bg=COLORS["surface"])
        keep_rounded(self.forgot, 24)

        width = 470
        height = 250
        x = self.panel.winfo_x() + (self.panel.winfo_width() - width) // 2
        y = self.panel.winfo_y() - height - 18
        if y < 16:
            y = self.panel.winfo_y() + self.panel.winfo_height() + 18
        self.forgot.geometry(geometry_string(width, height, x, y))

        answer = tk.StringVar()
        status = tk.StringVar(value="")
        frame = tk.Frame(self.forgot, bg=COLORS["surface"], padx=24, pady=22)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        tk.Label(frame, text="Recovery", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="ew")
        tk.Label(
            frame,
            text=self.config.data.get("security_question", ""),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            wraplength=410,
            justify="left",
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="ew", pady=(8, 12))
        entry = tk.Entry(frame, textvariable=answer, show="*", bg=COLORS["surface_2"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", font=("Segoe UI", 12))
        entry.grid(row=2, column=0, sticky="ew", ipady=8)
        self.recovery_entry = entry
        tk.Label(frame, textvariable=status, bg=COLORS["surface"], fg=COLORS["danger"], font=("Segoe UI", 9)).grid(row=3, column=0, sticky="ew", pady=(8, 8))
        row = tk.Frame(frame, bg=COLORS["surface"])
        row.grid(row=4, column=0, sticky="e")

        def check_answer():
            if self.config.verify_security_answer(answer.get()):
                self._close_forgot()
                self._unlock(open_change_password=True)
            else:
                status.set("Security answer did not match.")
                answer.set("")
                entry.focus_force()

        ttk.Button(row, text="Cancel", style="Ghost.Secondary.TButton", command=self._close_forgot).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Recover", style="Ghost.TButton", command=check_answer).pack(side="left")
        entry.bind("<Return>", lambda _event: check_answer(), add="+")
        entry.focus_force()
        return "break"

    def _close_forgot(self):
        try:
            if self.forgot and self.forgot.winfo_exists():
                self.forgot.destroy()
        except Exception:
            pass
        self.forgot = None
        self.recovery_entry = None
        self.focus()

    def _unlock(self, open_change_password=False, auto_release=False):
        if not self.active:
            return
        self.active = False
        for window in (self.forgot, self.panel, self.overlay):
            try:
                if window and window.winfo_exists():
                    window.destroy()
            except Exception:
                pass
        self.on_unlock()
        if open_change_password:
            self.root.after(250, lambda: ChangePasswordWindow(self.root, self.config))


def main():
    if platform.system() != "Windows":
        print("GhostLock is designed for Windows 10 and newer.")
    enable_dpi_awareness()
    if is_uninstall_invocation():
        root = tk.Tk()
        UninstallerWindow(root)
        root.mainloop()
        return
    if is_setup_invocation():
        root = tk.Tk()
        InstallerWindow(root)
        root.mainloop()
        return
    force_setup = is_forced_setup_invocation()
    if not acquire_single_instance():
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(APP_NAME, "GhostLock is already running.")
        root.destroy()
        return
    app = GhostLockApp(force_setup=force_setup)
    app.run()


if __name__ == "__main__":
    main()
