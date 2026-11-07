# ── stdlib ────────────────────────────────────────────────────
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request
# from __future__ import annotations
from typing import Dict
import ctypes
import datetime
import hashlib
import json
import os
import platform
import random
import re
import shutil
import smtplib
import subprocess
import threading
import time
import tkinter as tk
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from tkinter import messagebox, simpledialog


# ── third-party: bcrypt (required) ───────────────────────────
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("[SECURITY] WARNING: bcrypt not found. Install with: pip install bcrypt")

# ── third-party: optional ─────────────────────────────────────
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pyrebase
    PYREBASE_AVAILABLE = True
except ImportError:
    PYREBASE_AVAILABLE = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

# FIX: python-magic imported safely with clear fallback flag
# If not installed, MIME detection is skipped (scan continues via extension check)
try:
    import magic as _magic_lib
    MAGIC_AVAILABLE = True
    print("[SCANNER] python-magic available – MIME detection enabled.")
except ImportError:
    _magic_lib      = None
    MAGIC_AVAILABLE = False
    print("[SCANNER] python-magic not installed – MIME detection disabled. "
          "Install with: pip install python-magic python-magic-bin")


# ══════════════════════════════════════════════════════════════
#  CREDENTIALS – load from environment variables
# ══════════════════════════════════════════════════════════════
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# FIX: Hardcoded for testing
SMTP_USER = "ehacking80@gmail.com"
SMTP_PASS = "zhcermabkppqeujv"

if not SMTP_USER:
    print("[EMAIL] WARNING: SMTP_USER environment variable is not set. "
          "Email alerts will NOT be sent.")
if not SMTP_PASS:
    print("[EMAIL] WARNING: SMTP_PASS environment variable is not set. "
          "Email alerts will NOT be sent.")


def _load_firebase_config() -> dict:
    required = [
        "AIzaSyCCdhuAB_7AbaspZ4V9GWzwnQF7Kqkt2Zw", "darkwatch-usb.firebaseapp.com", "https://darkwatch-usb-default-rtdb.firebaseio.com/",
        "darkwatch-usb", "darkwatch-usb.firebasestorage.app",
        "182942827791", "1:182942827791:web:98e3d823e661f853deaa7a",
    ]
    if not all(os.getenv(k) for k in required):
        return {}
    return {
        "apiKey":            os.getenv("AIzaSyCCdhuAB_7AbaspZ4V9GWzwnQF7Kqkt2Zw"),
        "authDomain":        os.getenv("darkwatch-usb.firebaseapp.com"),
        "databaseURL":       os.getenv("https://darkwatch-usb-default-rtdb.firebaseio.com/"),
        "projectId":         os.getenv("darkwatch-usb"),
        "storageBucket":     os.getenv("darkwatch-usb.firebasestorage.app"),
        "messagingSenderId": os.getenv("182942827791"),
        "appId":             os.getenv("1:182942827791:web:98e3d823e661f853deaa7a"),
    }

_firebase_cfg = _load_firebase_config()
_firebase_db  = None

if _firebase_cfg and PYREBASE_AVAILABLE:
    try:
        _fb          = pyrebase.initialize_app(_firebase_cfg)
        _firebase_db = _fb.database()
        print("[FIREBASE] Connected successfully.")
    except Exception as _fb_exc:
        print(f"[FIREBASE] Init failed: {_fb_exc}")
        _firebase_db = None
else:
    print("[FIREBASE] Config missing or pyrebase not installed – Firebase disabled.")


def firebase_push(node: str, data: dict) -> bool:
    if _firebase_db is None:
        return False
    try:
        _firebase_db.child(node).push(data)
        return True
    except Exception as exc:
        print(f"[FIREBASE] Push error: {exc}")
        return False
SERVICE_ACCOUNT_FILE = "serviceAccountKey.json"
PROJECT_ID = "darkwatch-usb"

def get_access_token():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )
    credentials.refresh(Request())
    return credentials.token

def send_push(title, body):
    access_token = get_access_token()

    url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    data = {
        "message": {
            "topic": "usb_alerts",
            "notification": {
                "title": title,
                "body": body
            }
        }
    }

    response = requests.post(url, headers=headers, json=data)
    print("FCM Response:", response.text)

# ══════════════════════════════════════════════════════════════
#  CONSTANTS & THEME
# ══════════════════════════════════════════════════════════════
APP_TITLE = "USB Guardian"
WIN_W     = 1100
WIN_H     = 640

BG_DARK  = "#0b0c10"
BG_MID   = "#111217"
BG_CARD  = "#16181f"
BG_FIELD = "#1e2030"
BG_HOVER = "#1e2535"
BORDER   = "#2a2d3e"

BLUE1     = "#3a7bd5"
BLUE2     = "#00d2ff"
BTN_HOVER = "#2a6bc5"

ACCENT_RED  = "#e74c3c"
ACCENT_GRN  = "#2ecc71"
ACCENT_YLW  = "#f39c12"
ACCENT_DARK = "#16213e"

TEXT_WH = "#f0f0f0"
TEXT_GR = "#8a8f9e"
TEXT_MT = "#4a4f5e"

F_TITLE = ("Georgia",    20, "bold")
F_HEAD  = ("Georgia",    14, "bold")
F_BODY  = ("Courier",    10)
F_SMALL = ("Courier",     9)
F_MONO  = ("Courier New", 9)
F_LABEL = ("Courier",    11)

BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
PHOTO_DIR  = DATA_DIR / "photos"
ACCOUNTS_F = DATA_DIR / "accounts.json"
LOG_F      = DATA_DIR / "activity_log.json"

for _d in (DATA_DIR, PHOTO_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SUSPICIOUS_EXT = {
    ".exe", ".bat", ".cmd", ".vbs", ".ps1", ".scr",
    ".pif", ".com", ".jar", ".msi", ".dll",
}

# FIX: suspicious MIME types for MIME-based detection
SUSPICIOUS_MIME = {
    "application/x-dosexec",          # PE executables (.exe, .dll)
    "application/x-msdos-program",    # DOS programs
    "application/x-msdownload",       # Windows download
    "application/x-executable",       # Generic executables
    "application/x-shellscript",      # Shell scripts
    "application/x-bat",              # Batch files
    "application/java-archive",       # JAR files
    "application/x-ms-installer",     # MSI installers
}

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECS = 300


# ══════════════════════════════════════════════════════════════
#  ADMIN PRIVILEGE CHECK
# ══════════════════════════════════════════════════════════════
def is_admin() -> bool:
    try:
        if platform.system() == "Windows":
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        else:
            return os.geteuid() == 0
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
#  INPUT VALIDATION
# ══════════════════════════════════════════════════════════════
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PW_MIN   = 8

def validate_email(email: str) -> tuple[bool, str]:
    if not email or not email.strip():
        return False, "Email is required."
    if not _EMAIL_RE.match(email.strip()):
        return False, "Invalid email address."
    return True, ""

def validate_password(pw: str) -> tuple[bool, str]:
    if not pw:
        return False, "Password is required."
    if len(pw) < _PW_MIN:
        return False, f"Password must be at least {_PW_MIN} characters."
    return True, ""


# ══════════════════════════════════════════════════════════════
#  SECURE PASSWORD HASHING
# ══════════════════════════════════════════════════════════════
def hash_pw(pw: str) -> str:
    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    print("[SECURITY] WARNING: Using SHA-256 fallback. Install bcrypt!")
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_pw(pw: str, stored: str) -> bool:
    if not pw or not stored:
        return False
    if BCRYPT_AVAILABLE:
        try:
            if stored.startswith("$2"):
                return bcrypt.checkpw(pw.encode(), stored.encode())
        except Exception as exc:
            print(f"[SECURITY] bcrypt verify error: {exc}")
            return False
    return hashlib.sha256(pw.encode()).hexdigest() == stored


# ══════════════════════════════════════════════════════════════
#  UTILITY HELPERS
# ══════════════════════════════════════════════════════════════
def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def short_time() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")

def gradient_rect(canvas, x1, y1, x2, y2, c1, c2, steps=60):
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    w = (x2 - x1) / max(steps, 1)
    for i in range(steps):
        t = i / max(steps - 1, 1)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        canvas.create_rectangle(
            x1 + i * w, y1, x1 + (i + 1) * w + 1, y2,
            fill=f"#{r:02x}{g:02x}{b:02x}", outline=""
        )

def make_gradient_btn(parent, label, cmd, w=220, h=38, bg=BG_MID):
    c = tk.Canvas(parent, width=w, height=h, bg=bg,
                  highlightthickness=0, cursor="hand2")
    def _draw(txt, c1, c2):
        c.delete("all")
        gradient_rect(c, 0, 0, w, h, c1, c2)
        c.create_text(w // 2, h // 2, text=txt,
                      fill="white", font=("Georgia", 11, "bold"))
    _draw(label, BLUE1, BLUE2)
    c.bind("<Button-1>", lambda e: cmd())
    c.bind("<Enter>",    lambda e: _draw(f"{label} →", BTN_HOVER, "#00b8e0"))
    c.bind("<Leave>",    lambda e: _draw(label, BLUE1, BLUE2))
    return c

def make_field(parent, placeholder, is_pw=False, icon="", width=24):
    wrap  = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
    wrap.pack(fill="x", pady=4)
    inner = tk.Frame(wrap, bg=BG_FIELD)
    inner.pack(fill="x")

    if not icon:
        ph   = placeholder.lower()
        icon = ("\U0001f512"  if is_pw
                else "\u2709" if ("email" in ph or "mail" in ph)
                else "\U0001f511" if ("otp" in ph or "code" in ph)
                else "\U0001f464")

    tk.Label(inner, text=icon, bg=BG_FIELD, fg=TEXT_GR,
             font=("Arial", 11), padx=8).pack(side="left")

    entry = tk.Entry(inner, bg=BG_FIELD, fg=TEXT_WH,
                     insertbackground=TEXT_WH,
                     relief="flat", font=F_LABEL,
                     bd=0, width=width,
                     show="\u25cf" if is_pw else "")
    entry.pack(side="left", ipady=9, padx=(0, 4))
    entry.insert(0, placeholder)
    entry.config(fg=TEXT_GR)

    real_show = "\u25cf" if is_pw else ""

    def _fi(e):
        if entry.get() == placeholder:
            entry.delete(0, "end")
            entry.config(fg=TEXT_WH, show=real_show if is_pw else "")
        wrap.config(bg=BLUE1)

    def _fo(e):
        if entry.get() == "":
            entry.insert(0, placeholder)
            entry.config(fg=TEXT_GR, show="")
        wrap.config(bg=BORDER)

    entry.bind("<FocusIn>",  _fi)
    entry.bind("<FocusOut>", _fo)

    if is_pw:
        def _tog():
            if entry.cget("show") == "\u25cf":
                entry.config(show="")
                eye.config(text="\u25cb")
            else:
                entry.config(show="\u25cf")
                eye.config(text="\u25cf")
        eye = tk.Button(inner, text="\u25cf", bg=BG_FIELD, fg=TEXT_GR,
                        relief="flat", bd=0, activebackground=BG_FIELD,
                        font=("Arial", 10), cursor="hand2", command=_tog)
        eye.pack(side="right", padx=8)

    return entry

def sidebar_btn(parent, text, cmd, icon="", accent=None):
    row   = tk.Frame(parent, bg=BG_CARD, cursor="hand2")
    row.pack(fill="x", pady=2)
    inner = tk.Frame(row, bg=BG_CARD)
    inner.pack(fill="x", padx=6, pady=1)

    if icon:
        tk.Label(inner, text=icon, bg=BG_CARD, fg=TEXT_GR,
                 font=("Arial", 13), width=2).pack(side="left")

    fg  = accent if accent else TEXT_GR
    lbl = tk.Label(inner, text=text, bg=BG_CARD, fg=fg,
                   font=("Courier", 10), anchor="w")
    lbl.pack(side="left", fill="x", expand=True, pady=6)

    def _in(e):
        for widget in (row, inner, lbl):
            widget.config(bg=BG_HOVER)
        for widget in inner.winfo_children():
            widget.config(bg=BG_HOVER)

    def _out(e):
        for widget in (row, inner, lbl):
            widget.config(bg=BG_CARD)
        for widget in inner.winfo_children():
            widget.config(bg=BG_CARD)

    targets = (row, inner, lbl) + tuple(inner.winfo_children())
    for widget in targets:
        widget.bind("<Button-1>", lambda e: cmd())
        widget.bind("<Enter>",    _in)
        widget.bind("<Leave>",    _out)

    return row

def separator(parent, color=BORDER):
    tk.Frame(parent, bg=color, height=1).pack(fill="x", padx=10, pady=6)

def status_pill(parent, text, color):
    return tk.Label(parent, text=f"  {text}  ",
                    bg=color, fg=BG_DARK,
                    font=("Courier", 8, "bold"),
                    padx=4, pady=2)


# ══════════════════════════════════════════════════════════════
#  ACCOUNT STORE
# ══════════════════════════════════════════════════════════════
class AccountStore:
    def __init__(self, path: Path = ACCOUNTS_F):
        self.path   = path
        self._data: dict = {}
        self._lock  = threading.Lock()
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    self._data = json.load(f)
            except Exception as exc:
                print(f"[ACCOUNTS] Load error: {exc}")
                self._data = {}

    def _save(self):
        tmp = self.path.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump(self._data, f, indent=2)
            tmp.replace(self.path)
        except Exception as exc:
            print(f"[ACCOUNTS] Save error: {exc}")
            if tmp.exists():
                tmp.unlink(missing_ok=True)

    def exists(self, email: str) -> bool:
        return email.lower().strip() in self._data

    def register(self, email: str, pw: str) -> tuple[bool, str]:
        ok, msg = validate_email(email)
        if not ok:
            return False, msg
        ok, msg = validate_password(pw)
        if not ok:
            return False, msg
        key = email.lower().strip()
        with self._lock:
            if key in self._data:
                return False, "Email already registered."
            self._data[key] = hash_pw(pw)
            self._save()
        return True, ""

    def verify(self, email: str, pw: str) -> bool:
        key    = email.lower().strip()
        stored = self._data.get(key)
        if not stored:
            return False
        return verify_pw(pw, stored)

    def update_password(self, email: str, new_pw: str) -> tuple[bool, str]:
        ok, msg = validate_password(new_pw)
        if not ok:
            return False, msg
        key = email.lower().strip()
        with self._lock:
            if key not in self._data:
                return False, "Account not found."
            self._data[key] = hash_pw(new_pw)
            self._save()
        return True, ""


# ══════════════════════════════════════════════════════════════
#  RATE LIMITER
# ══════════════════════════════════════════════════════════════
class RateLimiter:
    def __init__(self):
        self._attempts: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def record_failure(self, key: str):
        now = time.time()
        with self._lock:
            attempts = self._attempts.get(key, [])
            attempts.append(now)
            self._attempts[key] = [
                t for t in attempts if now - t < LOGIN_LOCKOUT_SECS
            ]

    def is_locked(self, key: str) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            attempts = [
                t for t in self._attempts.get(key, [])
                if now - t < LOGIN_LOCKOUT_SECS
            ]
            self._attempts[key] = attempts
            if len(attempts) >= MAX_LOGIN_ATTEMPTS:
                oldest = min(attempts)
                wait   = int(LOGIN_LOCKOUT_SECS - (now - oldest))
                return True, max(wait, 0)
        return False, 0

    def reset(self, key: str):
        with self._lock:
            self._attempts.pop(key, None)


# ══════════════════════════════════════════════════════════════
#  ACTIVITY LOGGER
# ══════════════════════════════════════════════════════════════
class ActivityLogger:
    def __init__(self, path: Path = LOG_F):
        self.path  = path
        self._data: list = []
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    self._data = json.load(f)
            except Exception as exc:
                print(f"[LOGGER] Load error: {exc}")
                self._data = []

    def _save(self):
        tmp = self.path.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump(self._data, f, indent=2)
            tmp.replace(self.path)
        except Exception as exc:
            print(f"[LOGGER] Save error: {exc}")
            if tmp.exists():
                tmp.unlink(missing_ok=True)

    def log(self, kind: str, event: str, detail: dict = None) -> dict:
        entry = {"ts": now_str(), "kind": kind, "event": event}
        if detail:
            entry.update(detail)
        with self._lock:
            self._data.append(entry)
            self._save()
        return entry

    def get_all(self) -> list:
        with self._lock:
            return list(reversed(self._data))

    def get_by_kind(self, kind: str) -> list:
        with self._lock:
            return [e for e in reversed(self._data) if e.get("kind") == kind]

    def clear(self):
        with self._lock:
            self._data = []
            self._save()


# ══════════════════════════════════════════════════════════════
#  CAMERA SERVICE
# ══════════════════════════════════════════════════════════════
class CameraService:
    @staticmethod
    def capture(filename: str = None) -> str | None:
        if not filename:
            ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = str(PHOTO_DIR / f"capture_{ts}.jpg")

        if not CV2_AVAILABLE:
            print("[CAMERA] cv2 not installed – using placeholder.")
            return CameraService._write_placeholder(filename)

        cap = None
        try:
            if platform.system() == "Windows":
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                print("[CAMERA] ERROR: camera not opened.")
                return CameraService._write_placeholder(filename)

            for _ in range(3):
                cap.read()

            ret, frame = cap.read()

            if not ret or frame is None or frame.size == 0:
                print("[CAMERA] ERROR: empty frame.")
                return CameraService._write_placeholder(filename)

            if not cv2.imwrite(filename, frame):
                print(f"[CAMERA] ERROR: imwrite failed → {filename}")
                return CameraService._write_placeholder(filename)

            print(f"[CAMERA] ✓ Captured → {filename}")
            return filename

        except Exception as exc:
            print(f"[CAMERA] Exception: {exc}")
            return CameraService._write_placeholder(filename)

        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

    @staticmethod
    def _write_placeholder(original_path: str) -> str | None:
        path = original_path.replace(".jpg", "_placeholder.png")
        try:
            png_1x1 = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
                b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
                b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            with open(path, "wb") as f:
                f.write(png_1x1)
            print(f"[CAMERA] Placeholder written → {path}")
            return path
        except Exception as exc:
            print(f"[CAMERA] ERROR writing placeholder: {exc}")
            return None


# ══════════════════════════════════════════════════════════════
#  FIX: EMAIL SERVICE
#  Changes:
#    • Validates SMTP_USER / SMTP_PASS from env with clear error logs
#    • 1-retry mechanism on transient failures
#    • Debug logging at every step: [EMAIL SENT] / [EMAIL FAILED]
#    • Validates recipient address before attempting send
#    • No silent failures anywhere
# ══════════════════════════════════════════════════════════════
class EmailService:
    """
    Sends email via Gmail SMTP + STARTTLS.
    Credentials MUST be set as environment variables:
    SMTP_USER = "ehacking80@gmail.com"
    SMTP_PASS = "zhcermabkppqeujv"
    """

    # FIX: Maximum retry attempts for transient SMTP failures
    _MAX_RETRIES = 1

    @staticmethod
    def _configured() -> tuple[bool, str]:
        """
        FIX: Returns (ok, error_message) with specific reason why unconfigured.
        Validates both fields are non-empty and email looks valid.
        """
        if not SMTP_USER:
            return False, ("SMTP_USER environment variable is not set. "
                           "Run: export SMTP_USER='you@gmail.com'")
        ok, err = validate_email(SMTP_USER)
        if not ok:
            return False, f"SMTP_USER '{SMTP_USER}' is not a valid email: {err}"
        if not SMTP_PASS:
            return False, ("SMTP_PASS environment variable is not set. "
                           "Run: export SMTP_PASS='your-app-password'")
        if len(SMTP_PASS) < 8:
            return False, ("SMTP_PASS appears too short. "
                           "Use a Gmail App Password (16 characters).")
        return True, ""

    @staticmethod
    def _attempt_send(msg_obj: MIMEMultipart, to: str) -> tuple[bool, str]:
        """
        FIX: Single SMTP send attempt with full exception granularity.
        Returns (ok, message).
        """
        try:
            print(f"[EMAIL] Connecting to {SMTP_HOST}:{SMTP_PORT} …")
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                print(f"[EMAIL] Authenticating as {SMTP_USER} …")
                server.login(SMTP_USER, SMTP_PASS)
                print(f"[EMAIL] Sending to {to} …")
                server.sendmail(SMTP_USER, [to], msg_obj.as_string())
            print(f"[EMAIL SENT] ✓ Successfully delivered to {to}")
            return True, "Email sent successfully."

        except smtplib.SMTPAuthenticationError as exc:
            err = (f"[EMAIL FAILED] AUTHENTICATION ERROR: {exc}\n"
                   "  → Use a Gmail App Password. "
                   "Enable 2FA then create an App Password at "
                   "https://myaccount.google.com/apppasswords")
            print(err)
            return False, err

        except smtplib.SMTPConnectError as exc:
            err = f"[EMAIL FAILED] CONNECT ERROR to {SMTP_HOST}:{SMTP_PORT}: {exc}"
            print(err)
            return False, err

        except smtplib.SMTPRecipientsRefused as exc:
            err = f"[EMAIL FAILED] RECIPIENT REFUSED ({to}): {exc}"
            print(err)
            return False, err

        except smtplib.SMTPServerDisconnected as exc:
            err = f"[EMAIL FAILED] SERVER DISCONNECTED: {exc}"
            print(err)
            return False, err

        except smtplib.SMTPException as exc:
            err = f"[EMAIL FAILED] SMTP ERROR: {exc}"
            print(err)
            return False, err

        except OSError as exc:
            err = (f"[EMAIL FAILED] NETWORK/OS ERROR: {exc}\n"
                   "  → Check internet connection and firewall/antivirus settings.")
            print(err)
            return False, err

        except Exception as exc:
            err = f"[EMAIL FAILED] UNEXPECTED ERROR ({type(exc).__name__}): {exc}"
            print(err)
            return False, err

    @staticmethod
    def send(to: str, subject: str, body: str,
             attachment_path: str = None) -> tuple[bool, str]:
        """
        FIX: Full send pipeline with credential validation, attachment handling,
        and retry logic. Returns (ok, message). Never raises.
        """
        # FIX: Validate recipient address first
        ok, err = validate_email(to)
        if not ok:
            msg = f"[EMAIL FAILED] Invalid recipient: {err}"
            print(msg)
            return False, msg

        # FIX: Validate credentials with specific error message
        configured, cfg_err = EmailService._configured()
        if not configured:
            msg = f"[EMAIL FAILED] Credentials not configured: {cfg_err}"
            print(msg)
            return False, msg

        # Build MIME message
        msg_obj            = MIMEMultipart()
        msg_obj["From"]    = SMTP_USER
        msg_obj["To"]      = to
        msg_obj["Subject"] = subject
        msg_obj.attach(MIMEText(body, "plain"))

        # FIX: Attach file with proper error handling
        if attachment_path:
            apath = Path(attachment_path)
            if apath.exists() and apath.is_file():
                try:
                    with open(apath, "rb") as fh:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(fh.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={apath.name}"
                    )
                    msg_obj.attach(part)
                    print(f"[EMAIL] Attachment added: {apath.name}")
                except Exception as exc:
                    # FIX: log but don't abort the send for attachment failures
                    print(f"[EMAIL] WARNING – could not attach '{attachment_path}': {exc}")
            else:
                print(f"[EMAIL] WARNING – attachment not found: {attachment_path}")

        # FIX: Retry loop (1 retry for transient failures)
        last_err = ""
        for attempt in range(1, EmailService._MAX_RETRIES + 2):  # 1 + retries
            if attempt > 1:
                print(f"[EMAIL] Retry attempt {attempt - 1} of {EmailService._MAX_RETRIES} …")
                time.sleep(2)  # brief pause before retry

            ok, last_err = EmailService._attempt_send(msg_obj, to)
            if ok:
                return True, last_err  # last_err contains success message here

            # FIX: Don't retry auth errors – they won't self-heal
            if "AUTHENTICATION" in last_err:
                print("[EMAIL] Authentication error – skipping retry.")
                break

        return False, last_err

    @staticmethod
    def send_otp(to: str, otp: str) -> tuple[bool, str]:
        body = (
            f"Your USB Guardian password reset OTP is: {otp}\n\n"
            "This code expires in 10 minutes.\n"
            "If you did not request this, ignore this email."
        )
        return EmailService.send(to, "USB Guardian – OTP Code", body)

    @staticmethod
    def send_usb_alert(to: str, device: str,
                       photo_path: str = None) -> tuple[bool, str]:
        """FIX: Triggered on every USB insert event."""
        body = (
            f"WARNING: USB DEVICE ALERT\n"
            f"{'=' * 40}\n"
            f"Device  : {device}\n"
            f"Time    : {now_str()}\n\n"
            "A USB device was inserted into your system.\n"
            "The device has been BLOCKED automatically.\n"
            "Review the activity log and allow only if trusted.\n"
        )
        print(f"[EMAIL] Sending USB insert alert to {to} for device: {device}")
        return EmailService.send(
            to, "WARNING: USB Guardian – Device Inserted", body, photo_path
        )

    @staticmethod
    def send_malware_alert(to: str, device: str,
                           found_files: list[str],
                           photo_path: str = None) -> tuple[bool, str]:
        """FIX: Triggered specifically on malware detection."""
        file_list = "\n".join(f"  • {f}" for f in found_files[:10])
        body = (
            f"CRITICAL: MALWARE DETECTED ON USB DEVICE\n"
            f"{'=' * 40}\n"
            f"Device  : {device}\n"
            f"Time    : {now_str()}\n"
            f"Files   : {len(found_files)} suspicious file(s) found\n\n"
            f"Suspicious files:\n{file_list}\n\n"
            "The device has been BLOCKED automatically.\n"
            "Do NOT allow this device until it is cleaned.\n"
        )
        print(f"[EMAIL] Sending malware alert to {to} – {len(found_files)} file(s) found")
        return EmailService.send(
            to, "CRITICAL: USB Guardian – Malware Detected", body, photo_path
        )


# ══════════════════════════════════════════════════════════════
#  FIX: MALWARE SCANNER
#  Changes:
#    • python-magic used safely with MAGIC_AVAILABLE guard
#    • FIX: 'file' variable replaced with 'full_path' everywhere
#    • SHA256 hashing added for each scanned file
#    • Per-file exception handling – scan loop NEVER crashes
#    • Deduplication of found files (extension + MIME may both flag same file)
#    • Proper [SCAN START] / [SCAN RESULT] logging
#    • Returns structured ScanResult with hash map for reporting
# ══════════════════════════════════════════════════════════════
class MalwareScanner:
    """
    Multi-layer USB malware scanner:
      Layer 1 – File extension matching (always runs)
      Layer 2 – MIME type detection via python-magic (if installed)
      Layer 3 – SHA256 hash of each suspicious file (for logging/reporting)

    All layers are independent. If any layer fails for a specific file,
    that file is skipped and scanning continues (no crash).
    """

    @staticmethod
    def _compute_sha256(full_path: str) -> str:
        """
        FIX: Compute SHA256 hash of a file for identification/reporting.
        Returns hex string or 'ERROR:<reason>' if file can't be read.
        """
        sha = hashlib.sha256()
        try:
            with open(full_path, "rb") as fh:
                # FIX: Read in chunks to handle large files without OOM
                while True:
                    chunk = fh.read(65536)
                    if not chunk:
                        break
                    sha.update(chunk)
            return sha.hexdigest()
        except PermissionError:
            return "ERROR:PermissionDenied"
        except OSError as exc:
            return f"ERROR:{exc.strerror}"
        except Exception as exc:
            return f"ERROR:{type(exc).__name__}"

    @staticmethod
    def _check_mime(full_path: str) -> tuple[bool, str]:
        """
        FIX: MIME type check using python-magic.
        Returns (is_suspicious, mime_type_string).
        Returns (False, 'unavailable') if python-magic not installed.
        Returns (False, 'error:<reason>') on per-file errors.
        """
        # FIX: Guard on MAGIC_AVAILABLE – never crash if not installed
        if not MAGIC_AVAILABLE:
            return False, "unavailable"

        try:
            # FIX: Use correct variable 'full_path' (was 'file' in original – BUG)
            mime = _magic_lib.from_file(full_path, mime=True)
            is_suspicious = mime in SUSPICIOUS_MIME
            return is_suspicious, mime
        except PermissionError:
            return False, "error:PermissionDenied"
        except FileNotFoundError:
            return False, "error:FileNotFound"
        except Exception as exc:
            # FIX: Log per-file MIME error but do NOT stop the scan loop
            print(f"[SCAN] MIME check error on '{full_path}': {exc}")
            return False, f"error:{type(exc).__name__}"

    @staticmethod
    def scan(path: str) -> tuple[bool, list[dict]]:
        """
        Scan the USB drive at *path* for malicious files.

        Returns:
          (clean: bool, found: list[dict])

        Each entry in 'found' is:
          {
            "path":      str,   # full file path
            "reason":    str,   # "extension" | "mime" | "extension+mime"
            "extension": str,   # file extension
            "mime":      str,   # detected MIME type or "unavailable"
            "sha256":    str,   # SHA256 hash of the file
          }
        """
        # FIX: [SCAN START] log so operator knows scan began
        print(f"[SCAN START] Scanning path: {path}")
        print(f"[SCAN START] MIME detection: {'enabled' if MAGIC_AVAILABLE else 'disabled (python-magic not installed)'}")

        # FIX: found uses dict keyed by path for deduplication
        found_map: dict[str, dict] = {}
        files_checked = 0
        files_skipped = 0

        try:
            for root_dir, dirs, files in os.walk(path):
                # FIX: limit recursion depth to 5 levels to avoid infinite loops
                depth = root_dir.replace(path, "").count(os.sep)
                if depth >= 5:
                    del dirs[:]
                    continue

                for fname in files:
                    # FIX: always use 'full_path' – never bare 'file' variable
                    full_path = os.path.join(root_dir, fname)
                    files_checked += 1

                    try:
                        # ── Skip if file no longer exists (race condition) ──
                        if not os.path.isfile(full_path):
                            files_skipped += 1
                            continue

                        ext           = Path(fname).suffix.lower()
                        flag_reason   = []
                        mime_detected = "unavailable"

                        # ── Layer 1: Extension check ─────────────────────
                        if ext in SUSPICIOUS_EXT:
                            flag_reason.append("extension")

                        # ── Layer 2: MIME type check ──────────────────────
                        # FIX: calls _check_mime with correct 'full_path' variable
                        is_sus_mime, mime_detected = MalwareScanner._check_mime(full_path)
                        if is_sus_mime:
                            flag_reason.append("mime")

                        if not flag_reason:
                            continue   # clean file – move on

                        # ── Layer 3: SHA256 hash ──────────────────────────
                        sha256 = MalwareScanner._compute_sha256(full_path)

                        # FIX: Deduplication – if already found by extension,
                        # update reason to "extension+mime" rather than adding duplicate
                        if full_path in found_map:
                            existing = found_map[full_path]
                            combined = set(existing["reason"].split("+")) | set(flag_reason)
                            existing["reason"] = "+".join(sorted(combined))
                        else:
                            found_map[full_path] = {
                                "path":      full_path,
                                "reason":    "+".join(flag_reason),
                                "extension": ext,
                                "mime":      mime_detected,
                                "sha256":    sha256,
                            }
                            print(f"[SCAN] ⚠ Suspicious: {full_path} "
                                  f"[reason={'+'.join(flag_reason)}, "
                                  f"mime={mime_detected}, sha256={sha256[:16]}…]")

                    except PermissionError:
                        # FIX: Permission errors are common on USB – skip silently
                        files_skipped += 1
                    except Exception as file_exc:
                        # FIX: Per-file exception – log and continue, NEVER crash loop
                        print(f"[SCAN] Error checking '{full_path}': {file_exc}")
                        files_skipped += 1

        except PermissionError as exc:
            print(f"[SCAN] Permission error accessing drive root '{path}': {exc}")
        except Exception as exc:
            print(f"[SCAN] Unexpected scan error: {exc}")

        found_list = list(found_map.values())
        clean      = len(found_list) == 0

        # FIX: [SCAN RESULT] log with full summary
        print(f"[SCAN RESULT] Path: {path}")
        print(f"[SCAN RESULT] Files checked : {files_checked}")
        print(f"[SCAN RESULT] Files skipped : {files_skipped}")
        print(f"[SCAN RESULT] Threats found : {len(found_list)}")
        print(f"[SCAN RESULT] Status        : {'CLEAN' if clean else 'THREATS DETECTED'}")

        return clean, found_list

    @staticmethod
    def format_report(found: list[dict]) -> str:
        """
        FIX: Human-readable scan report for UI display and email body.
        """
        if not found:
            return "No suspicious files found."
        lines = [f"{len(found)} suspicious file(s) detected:\n"]
        for i, item in enumerate(found[:20], 1):
            lines.append(
                f"  {i}. {item['path']}\n"
                f"     Reason   : {item['reason']}\n"
                f"     MIME     : {item['mime']}\n"
                f"     SHA256   : {item['sha256'][:32]}…\n"
            )
        if len(found) > 20:
            lines.append(f"  … and {len(found) - 20} more.")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
#  WATCHDOG HANDLER
# ══════════════════════════════════════════════════════════════
class _BlockedDriveWatcher(
    FileSystemEventHandler if WATCHDOG_AVAILABLE else object
):
    def __init__(self, drive_path: str):
        self.drive_root = Path(drive_path).resolve()
        if WATCHDOG_AVAILABLE:
            super().__init__()

    def _safe_nuke(self, raw_path: str):
        try:
            target = Path(raw_path).resolve()
            if self.drive_root not in target.parents and target != self.drive_root:
                print(f"[WATCHER] Blocked unsafe deletion attempt: {raw_path}")
                return
            if target.is_file():
                target.unlink()
                print(f"[WATCHER] ✓ File deleted: {target}")
            elif target.is_dir():
                shutil.rmtree(target, ignore_errors=False)
                print(f"[WATCHER] ✓ Dir deleted: {target}")
        except PermissionError as exc:
            print(f"[WATCHER] Permission denied: {raw_path}: {exc}")
        except Exception as exc:
            print(f"[WATCHER] Could not delete {raw_path}: {exc}")

    def on_created(self, event):
        self._safe_nuke(event.src_path)

    def on_moved(self, event):
        self._safe_nuke(event.dest_path)


# ══════════════════════════════════════════════════════════════
#  USB BLOCKER
# ══════════════════════════════════════════════════════════════
class USBBlocker:
    _observers: Dict[str, "Observer"] = {}
    _lock = threading.Lock()

    @classmethod
    def block(cls, path: str) -> tuple[bool, str]:
        print(f"[USB BLOCK] Blocking {path}")
        if platform.system() == "Windows":
            return cls._block_windows(path)
        return cls._block_unix(path)

    @classmethod
    def unblock(cls, path: str) -> tuple[bool, str]:
        print(f"[USB BLOCK] Unblocking {path}")
        if platform.system() == "Windows":
            return cls._unblock_windows(path)
        return cls._unblock_unix(path)

    @classmethod
    def _block_windows(cls, path: str) -> tuple[bool, str]:
        results = []
        if not is_admin():
            print("[USB BLOCK] WARNING: Not running as Administrator.")

        reg_ok,   reg_msg   = cls._registry_write_protect(enable=True)
        acl_ok,   acl_msg   = cls._icacls_deny(path, deny=True)
        watch_ok, watch_msg = cls._start_watcher(path)

        results.append(f"Registry: {'OK' if reg_ok else 'FAILED'}")
        results.append(f"icacls: {'OK' if acl_ok else 'FAILED'}")
        results.append(f"Watcher: {'OK' if watch_ok else 'FAILED'}")

        overall = reg_ok or acl_ok or watch_ok
        summary = f"Block on {path}: {' | '.join(results)}"
        print(f"[USB BLOCK] {'SUCCESS' if overall else 'FAILED'}: {summary}")
        return overall, summary

    @classmethod
    def _unblock_windows(cls, path: str) -> tuple[bool, str]:
        results = []
        if not is_admin():
            print("[USB BLOCK] WARNING: Not running as Administrator.")

        reg_ok,   _ = cls._registry_write_protect(enable=False)
        acl_ok,   _ = cls._icacls_deny(path, deny=False)
        watch_ok, _ = cls._stop_watcher(path)

        results.append(f"Registry: {'OK' if reg_ok else 'FAILED'}")
        results.append(f"icacls: {'OK' if acl_ok else 'FAILED'}")
        results.append(f"Watcher: {'OK' if watch_ok else 'FAILED'}")

        overall = reg_ok or acl_ok
        summary = f"Unblock on {path}: {' | '.join(results)}"
        print(f"[USB BLOCK] Unblock {'SUCCESS' if overall else 'FAILED'}: {summary}")
        return overall, summary

    @staticmethod
    def _registry_write_protect(enable: bool) -> tuple[bool, str]:
        reg_path = r"SYSTEM\CurrentControlSet\Control\StorageDevicePolicies"
        value    = 1 if enable else 0
        label    = "ENABLE" if enable else "DISABLE"

        try:
            import winreg
            key = winreg.CreateKeyEx(
                winreg.HKEY_LOCAL_MACHINE, reg_path, 0,
                winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
            )
            winreg.SetValueEx(key, "WriteProtect", 0, winreg.REG_DWORD, value)
            winreg.CloseKey(key)
            msg = f"Registry WriteProtect={value} ({label}) via winreg."
            print(f"[REGISTRY] ✓ {msg}")
            return True, msg
        except PermissionError:
            print("[REGISTRY] PermissionError – trying reg.exe …")
        except Exception as exc:
            print(f"[REGISTRY] winreg error: {exc} – trying reg.exe …")

        try:
            cmd = [
                "reg", "add",
                r"HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies",
                "/v", "WriteProtect", "/t", "REG_DWORD",
                "/d", str(value), "/f"
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                msg = f"Registry WriteProtect={value} ({label}) via reg.exe."
                print(f"[REGISTRY] ✓ {msg}")
                return True, msg
            err = f"reg.exe rc={result.returncode}: {result.stderr.strip()}"
            print(f"[REGISTRY] ✗ {err}")
            return False, err
        except Exception as exc:
            err = f"reg.exe exception: {exc}"
            print(f"[REGISTRY] ✗ {err}")
            return False, err

    @staticmethod
    def _icacls_deny(path: str, deny: bool) -> tuple[bool, str]:
        drive = path.rstrip("\\")
        if deny:
    # FIX: Correct ACL syntax
            cmd = ["icacls", drive, "/deny",
                "Everyone:(W)", "/T", "/C", "/Q"]
        else:
            cmd = ["icacls", drive, "/remove:d", "Everyone", "/T", "/C", "/Q"]

        print(f"[ICACLS] Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                msg = f"icacls {'DENY' if deny else 'RESTORE'} OK on {drive}"
                print(f"[ICACLS] ✓ {msg}")
                return True, msg
            err = (f"icacls rc={result.returncode}: "
                   f"{(result.stderr or result.stdout).strip()[:200]}")
            print(f"[ICACLS] ✗ {err}")
            return False, err
        except subprocess.TimeoutExpired:
            err = "icacls timed out."
            print(f"[ICACLS] ✗ {err}")
            return False, err
        except FileNotFoundError:
            err = "icacls.exe not found."
            print(f"[ICACLS] ✗ {err}")
            return False, err
        except Exception as exc:
            err = f"icacls exception: {exc}"
            print(f"[ICACLS] ✗ {err}")
            return False, err

    @classmethod
    def _start_watcher(cls, path: str) -> tuple[bool, str]:
        if not WATCHDOG_AVAILABLE:
            return False, "watchdog not installed (pip install watchdog)."
        cls._stop_watcher(path)
        try:
            handler  = _BlockedDriveWatcher(path)
            observer = Observer()
            observer.schedule(handler, path=path, recursive=True)
            observer.start()
            with cls._lock:
                cls._observers[path] = observer
            msg = f"Watchdog started on {path}"
            print(f"[WATCHER] ✓ {msg}")
            return True, msg
        except Exception as exc:
            err = f"Watchdog start error: {exc}"
            print(f"[WATCHER] ✗ {err}")
            return False, err

    @classmethod
    def _stop_watcher(cls, path: str) -> tuple[bool, str]:
        with cls._lock:
            observer = cls._observers.pop(path, None)
        if observer is None:
            return True, "No active watcher for this path."
        try:
            observer.stop()
            observer.join(timeout=3)
            print(f"[WATCHER] ✓ Stopped watcher for {path}")
            return True, "Watcher stopped."
        except Exception as exc:
            err = f"Watchdog stop error: {exc}"
            print(f"[WATCHER] ✗ {err}")
            return False, err

    @classmethod
    def _block_unix(cls, path: str) -> tuple[bool, str]:
        if not is_admin():
            print("[USB BLOCK] WARNING: remount requires root.")
        ok, msg = cls._remount_unix(path, readonly=True)
        if ok:
            cls._start_watcher(path)
            return True, f"Remounted read-only. {msg}"
        try:
            r = subprocess.run(
                ["chmod", "-R", "a-w", path],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0:
                cls._start_watcher(path)
                return True, f"chmod a-w applied on {path}"
            err = f"chmod failed: {r.stderr.strip()}"
            print(f"[USB BLOCK] ✗ {err}")
            return False, err
        except Exception as exc:
            err = f"chmod exception: {exc}"
            print(f"[USB BLOCK] ✗ {err}")
            return False, err

    @classmethod
    def _unblock_unix(cls, path: str) -> tuple[bool, str]:
        cls._stop_watcher(path)
        ok, msg = cls._remount_unix(path, readonly=False)
        if ok:
            return True, f"Remounted read-write. {msg}"
        try:
            r = subprocess.run(
                ["chmod", "-R", "a+w", path],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0:
                return True, f"chmod a+w applied on {path}"
            return False, f"chmod +w failed: {r.stderr.strip()}"
        except Exception as exc:
            return False, f"chmod +w exception: {exc}"

    @staticmethod
    def _remount_unix(path: str, readonly: bool) -> tuple[bool, str]:
        option = "ro" if readonly else "rw"
        try:
            r = subprocess.run(
                ["mount", "-o", f"remount,{option}", path],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                return True, f"remount,{option} OK"
            return False, f"remount failed: {r.stderr.strip()}"
        except Exception as exc:
            return False, f"remount exception: {exc}"


# ══════════════════════════════════════════════════════════════
#  USB MONITOR
# ══════════════════════════════════════════════════════════════
class USBMonitor:
    def __init__(self, root: tk.Tk, on_connect, on_disconnect):
        self.root          = root
        self.on_connect    = on_connect
        self.on_disconnect = on_disconnect
        self._running      = False
        self._known: set   = set()
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="USBMonitorThread"
        )
        self._thread.start()
        print("[USB MONITOR] Started.")

    def stop(self):
        self._running = False
        print("[USB MONITOR] Stopped.")

    def _loop(self):
        while self._running:
            try:
                current = {d["path"]: d for d in self.get_usb_drives()}
                cur_set = set(current.keys())
                added   = cur_set - self._known
                removed = self._known - cur_set

                for path in added:
                    dev = current[path]
                    print(f"[USB MONITOR] New device: {path}. Blocking …")
                    try:
                        USBBlocker.block(path)
                    except Exception as block_exc:
                        print(f"[USB MONITOR] Block error: {block_exc}")
                    self.root.after(0, lambda d=dev: self.on_connect(d))

                for path in removed:
                    self.root.after(0, lambda p=path: self.on_disconnect(p))

                self._known = cur_set

            except Exception as exc:
                print(f"[USB MONITOR] Poll error (non-fatal): {exc}")

            time.sleep(0.1)

    def get_usb_drives(self) -> list[dict]:
        system = platform.system()
        if system == "Windows":
            return self._scan_windows()
        if system == "Linux":
            return self._scan_linux()
        if system == "Darwin":
            return self._scan_macos()
        return []

    def _scan_windows(self) -> list[dict]:
        drives = []
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if bitmask & (1 << i):
                    letter = chr(65 + i)
                    path   = f"{letter}:\\"
                    dtype  = ctypes.windll.kernel32.GetDriveTypeW(path)
                    if dtype == 2:
                        try:
                            total = ctypes.c_ulonglong(0)
                            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                                path, None, ctypes.byref(total), None
                            )
                            size_gb = round(total.value / 1e9, 1)
                        except Exception:
                            size_gb = 0
                        drives.append({
                            "name":    f"USB Drive ({letter}:)",
                            "path":    path,
                            "size_gb": size_gb,
                        })
        except Exception as exc:
            print(f"[USB SCAN WINDOWS] {exc}")
        return drives

    def _scan_linux(self) -> list[dict]:
        drives = []
        try:
            result = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,TRAN,MOUNTPOINT,SIZE,LABEL"],
                capture_output=True, text=True, timeout=5
            )
            data = json.loads(result.stdout)
            for dev in data.get("blockdevices", []):
                if dev.get("tran") == "usb":
                    for child in dev.get("children", [dev]):
                        mp = child.get("mountpoint")
                        if mp:
                            label = child.get("label") or child.get("name")
                            drives.append({
                                "name":    f"{label} ({mp})",
                                "path":    mp,
                                "size_gb": child.get("size", "?"),
                            })
        except Exception as exc:
            print(f"[USB SCAN LINUX] {exc}")
        return drives

    def _scan_macos(self) -> list[dict]:
        drives = []
        try:
            vol_dir = Path("/Volumes")
            for vol in vol_dir.iterdir():
                if vol.name in ("Macintosh HD", "Recovery"):
                    continue
                if vol.is_dir():
                    try:
                        st      = os.statvfs(vol)
                        size_gb = round(st.f_blocks * st.f_frsize / 1e9, 1)
                    except Exception:
                        size_gb = 0
                    drives.append({
                        "name":    vol.name,
                        "path":    str(vol),
                        "size_gb": size_gb,
                    })
        except Exception as exc:
            print(f"[USB SCAN MACOS] {exc}")
        return drives


# ══════════════════════════════════════════════════════════════
#  AUTHENTICATION VIEW
# ══════════════════════════════════════════════════════════════
class AuthView:
    def __init__(self, parent: tk.Frame, store: AccountStore,
                 logger: ActivityLogger, limiter: RateLimiter, on_success):
        self.parent     = parent
        self.store      = store
        self.logger     = logger
        self.limiter    = limiter
        self.on_success = on_success
        self._otp_store: dict = {"value": None, "ts": 0.0}

        self._lf = tk.Frame(parent, bg=BG_MID)
        self._sf = tk.Frame(parent, bg=BG_MID)
        self._ff = tk.Frame(parent, bg=BG_MID)

        self._build_login()
        self._build_signup()
        self._build_forgot()
        self.show_login()

    def show_login(self):
        self._sf.place_forget()
        self._ff.place_forget()
        self._lf.place(relx=.5, rely=.5, anchor="center")

    def show_signup(self):
        self._lf.place_forget()
        self._ff.place_forget()
        self._reset_signup()
        self._sf.place(relx=.5, rely=.5, anchor="center")

    def show_forgot(self):
        self._lf.place_forget()
        self._sf.place_forget()
        self._reset_forgot()
        self._ff.place(relx=.5, rely=.5, anchor="center")

    def _build_login(self):
        f = self._lf

        av = tk.Canvas(f, width=64, height=64, bg=BG_MID, highlightthickness=0)
        av.pack(pady=(0, 12))
        av.create_oval(2, 2, 62, 62, fill="#16213e", outline=BLUE1, width=2)
        av.create_oval(22, 10, 42, 30, fill="#c9a87c", outline="")
        av.create_arc(12, 30, 52, 62, start=0, extent=180, fill=BLUE1, outline="")

        tk.Label(f, text="Sign In",
                 bg=BG_MID, fg=TEXT_WH, font=F_TITLE).pack(pady=(0, 4))
        tk.Label(f, text="USB Guardian · Secure Access",
                 bg=BG_MID, fg=TEXT_GR, font=F_SMALL).pack(pady=(0, 18))

        self._l_email = make_field(f, "Email address")
        self._l_pass  = make_field(f, "Password", is_pw=True)

        make_gradient_btn(f, "LOGIN", self._do_login).pack(pady=(16, 8))

        self._l_status = tk.Label(f, text="", bg=BG_MID, fg=ACCENT_RED,
                                  font=F_SMALL, wraplength=260)
        self._l_status.pack(pady=(0, 4))

        fl = tk.Label(f, text="Forgot Password?", bg=BG_MID, fg=TEXT_GR,
                      font=(F_SMALL[0], F_SMALL[1], "underline"), cursor="hand2")
        fl.pack(pady=(0, 16))
        fl.bind("<Enter>",    lambda e: fl.config(fg=BLUE2))
        fl.bind("<Leave>",    lambda e: fl.config(fg=TEXT_GR))
        fl.bind("<Button-1>", lambda e: self.show_forgot())

        row = tk.Frame(f, bg=BG_MID)
        row.pack()
        tk.Label(row, text="No account?  ",
                 bg=BG_MID, fg=TEXT_MT, font=F_SMALL).pack(side="left")
        su = tk.Label(row, text="SIGN UP", bg=BG_MID, fg=BLUE1,
                      font=(F_SMALL[0], F_SMALL[1], "bold"), cursor="hand2")
        su.pack(side="left")
        su.bind("<Enter>",    lambda e: su.config(fg=BLUE2))
        su.bind("<Leave>",    lambda e: su.config(fg=BLUE1))
        su.bind("<Button-1>", lambda e: self.show_signup())

        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", pady=14)
        tk.Label(f, text="— or continue with —",
                 bg=BG_MID, fg=TEXT_MT, font=F_SMALL).pack(pady=(0, 6))
        social_row = tk.Frame(f, bg=BG_MID)
        social_row.pack()
        for icon, name in [("\U0001f310", "Google"),
                           ("\U0001f465", "Facebook"),
                           ("\uf8ff",     "Apple")]:
            b = tk.Label(social_row, text=f"{icon} {name}",
                         bg=BG_FIELD, fg=TEXT_GR,
                         font=F_SMALL, padx=10, pady=6, cursor="hand2")
            b.pack(side="left", padx=4)
            b.bind("<Enter>", lambda e, w=b: w.config(bg=BG_HOVER, fg=TEXT_WH))
            b.bind("<Leave>", lambda e, w=b: w.config(bg=BG_FIELD, fg=TEXT_GR))
            b.bind("<Button-1>", lambda e, n=name: (
                self.logger.log("admin", f"Social login attempt: {n}"),
                messagebox.showinfo(
                    "Social Login",
                    f"'{n}' login is simulated.\nUse email + password instead."
                )
            ))

    def _do_login(self):
        email = self._l_email.get().strip()
        pw    = self._l_pass.get()
        if email == "Email address": email = ""
        if pw    == "Password":      pw    = ""

        ok, err = validate_email(email)
        if not ok:
            self._l_status.config(text=err)
            return

        locked, wait = self.limiter.is_locked(email.lower())
        if locked:
            self._l_status.config(text=f"Account locked. Try again in {wait}s.")
            return

        if not self.store.verify(email, pw):
            self.limiter.record_failure(email.lower())
            attempts = self._attempts_left(email)
            self._l_status.config(
                text=f"Incorrect email or password. ({attempts} attempt(s) left)"
            )
            self.logger.log("attacker", "Failed login attempt", {"email": email})
            return

        self.limiter.reset(email.lower())
        self._l_status.config(text="")
        self.logger.log("admin", "Successful login", {"email": email})
        self.on_success(email)

    def _attempts_left(self, email: str) -> int:
        used = len([
            t for t in self.limiter._attempts.get(email.lower(), [])
            if time.time() - t < LOGIN_LOCKOUT_SECS
        ])
        return max(MAX_LOGIN_ATTEMPTS - used, 0)

    def _build_signup(self):
        f = self._sf

        sp_av = tk.Canvas(f, width=64, height=64, bg=BG_MID, highlightthickness=0)
        sp_av.pack(pady=(0, 10))
        sp_av.create_oval(2, 2, 62, 62, fill="#16213e", outline=BLUE1, width=2)
        sp_av.create_oval(22, 10, 42, 30, fill="#c9a87c", outline="")
        sp_av.create_arc(12, 30, 52, 62, start=0, extent=180, fill=BLUE1, outline="")
        sp_av.create_oval(40, 40, 58, 58, fill=BLUE2, outline=BG_MID, width=2)
        sp_av.create_text(49, 49, text="+", fill=BG_DARK, font=("Arial", 12, "bold"))

        tk.Label(f, text="Create Account",
                 bg=BG_MID, fg=TEXT_WH, font=F_TITLE).pack(pady=(0, 4))
        tk.Label(f, text="Join USB Guardian today",
                 bg=BG_MID, fg=TEXT_GR, font=F_SMALL).pack(pady=(0, 14))

        self._su_email = make_field(f, "Email address")
        self._su_pw1   = make_field(f, "Password",         is_pw=True)
        self._su_pw2   = make_field(f, "Confirm password", is_pw=True)

        make_gradient_btn(f, "CREATE ACCOUNT", self._do_signup).pack(pady=(14, 6))

        self._su_status = tk.Label(f, text="", bg=BG_MID, fg=ACCENT_RED,
                                   font=F_SMALL, wraplength=260)
        self._su_status.pack(pady=(0, 6))

        bk = tk.Label(f, text="\u2190 Back to Sign In", bg=BG_MID, fg=TEXT_GR,
                      font=(F_SMALL[0], F_SMALL[1], "underline"), cursor="hand2")
        bk.pack()
        bk.bind("<Enter>",    lambda e: bk.config(fg=BLUE2))
        bk.bind("<Leave>",    lambda e: bk.config(fg=TEXT_GR))
        bk.bind("<Button-1>", lambda e: self.show_login())

    def _reset_signup(self):
        for entry, ph in [(self._su_email, "Email address"),
                          (self._su_pw1,   "Password"),
                          (self._su_pw2,   "Confirm password")]:
            entry.delete(0, "end")
            entry.insert(0, ph)
            entry.config(fg=TEXT_GR, show="")
        self._su_status.config(text="")

    def _do_signup(self):
        email = self._su_email.get().strip()
        pw1   = self._su_pw1.get()
        pw2   = self._su_pw2.get()

        if email == "Email address":    email = ""
        if pw1   == "Password":         pw1   = ""
        if pw2   == "Confirm password": pw2   = ""

        ok, msg = validate_email(email)
        if not ok:
            self._su_status.config(text=msg); return

        ok, msg = validate_password(pw1)
        if not ok:
            self._su_status.config(text=msg); return

        if pw1 != pw2:
            self._su_status.config(text="Passwords do not match."); return

        ok, msg = self.store.register(email, pw1)
        if not ok:
            self._su_status.config(text=msg); return

        self.logger.log("admin", "New account created", {"email": email})
        self._su_status.config(text="Account created! Returning to login…", fg=BLUE2)
        self._sf.after(1200, self.show_login)

    def _build_forgot(self):
        f = self._ff

        lk = tk.Canvas(f, width=64, height=64, bg=BG_MID, highlightthickness=0)
        lk.pack(pady=(0, 10))
        lk.create_oval(2, 2, 62, 62, fill="#16213e", outline=BLUE1, width=2)
        lk.create_rectangle(20, 30, 44, 50, fill=BLUE1, outline="")
        lk.create_arc(20, 18, 44, 38, start=0, extent=180,
                      fill="", outline=BLUE2, width=3)
        lk.create_oval(29, 36, 35, 42, fill=BG_MID, outline="")

        tk.Label(f, text="Reset Password",
                 bg=BG_MID, fg=TEXT_WH, font=F_TITLE).pack(pady=(0, 4))
        self._fp_sub = tk.Label(f, text="Enter your email to receive an OTP",
                                bg=BG_MID, fg=TEXT_GR, font=F_SMALL)
        self._fp_sub.pack(pady=(0, 14))

        self._fp_email = make_field(f, "Email address")
        self._btn_send = make_gradient_btn(f, "SEND OTP", self._send_otp)
        self._btn_send.pack(pady=(12, 4))

        self._fp_status = tk.Label(f, text="", bg=BG_MID, fg=TEXT_GR,
                                   font=F_SMALL, wraplength=260)
        self._fp_status.pack(pady=(0, 2))

        self._fp_otp  = make_field(f, "Enter 6-digit OTP")
        self._fp_pw1  = make_field(f, "New password",     is_pw=True)
        self._fp_pw2  = make_field(f, "Confirm password", is_pw=True)
        self._btn_sub = make_gradient_btn(f, "SUBMIT", self._submit_reset)

        self._fp_back = tk.Label(f, text="\u2190 Back to Sign In",
                                 bg=BG_MID, fg=TEXT_GR,
                                 font=(F_SMALL[0], F_SMALL[1], "underline"),
                                 cursor="hand2")
        self._fp_back.bind("<Enter>",    lambda e: self._fp_back.config(fg=BLUE2))
        self._fp_back.bind("<Leave>",    lambda e: self._fp_back.config(fg=TEXT_GR))
        self._fp_back.bind("<Button-1>", lambda e: self.show_login())

    def _reset_forgot(self):
        self._otp_store = {"value": None, "ts": 0.0}
        for entry, ph in [(self._fp_email, "Email address"),
                          (self._fp_otp,   "Enter 6-digit OTP"),
                          (self._fp_pw1,   "New password"),
                          (self._fp_pw2,   "Confirm password")]:
            entry.delete(0, "end")
            entry.insert(0, ph)
            entry.config(fg=TEXT_GR, show="")
        self._fp_status.config(text="", fg=TEXT_GR)
        self._fp_sub.config(text="Enter your email to receive an OTP")
        self._fp_otp.master.master.pack_forget()
        self._fp_pw1.master.master.pack_forget()
        self._fp_pw2.master.master.pack_forget()
        self._btn_sub.pack_forget()
        self._btn_send.pack(pady=(12, 4))
        self._fp_status.pack(pady=(0, 2))
        self._fp_back.pack(pady=(10, 0))

    def _send_otp(self):
        email = self._fp_email.get().strip()
        if email == "Email address": email = ""

        ok, err = validate_email(email)
        if not ok:
            self._fp_status.config(text=err, fg=ACCENT_RED); return

        if not self.store.exists(email):
            self._fp_status.config(
                text="If that email is registered, an OTP has been sent.",
                fg=BLUE2
            )
            return

        otp = str(random.randint(100_000, 999_999))
        # FIX: Store SHA256 of OTP (not plaintext) to prevent memory exposure
        self._otp_store = {
            "value": hashlib.sha256(otp.encode()).hexdigest(),
            "ts":    time.time()
        }
        print(f"[OTP] Generated for {email} (not logged for security)")

        ok, msg = EmailService.send_otp(email, otp)
        self._fp_status.config(
            text="OTP sent – check your inbox." if ok else "Email error – check console.",
            fg=BLUE2 if ok else ACCENT_YLW
        )
        self._fp_sub.config(text="Check your inbox – enter OTP below")

        self._fp_otp.master.master.pack(fill="x", pady=4)
        self._fp_pw1.master.master.pack(fill="x", pady=4)
        self._fp_pw2.master.master.pack(fill="x", pady=4)
        self._btn_send.pack_forget()
        self._btn_sub.pack(pady=(12, 4))
        self._fp_back.pack_forget()
        self._fp_back.pack(pady=(10, 0))

    def _submit_reset(self):
        entered = self._fp_otp.get().strip()
        p1      = self._fp_pw1.get()
        p2      = self._fp_pw2.get()

        if entered == "Enter 6-digit OTP": entered = ""
        if p1      == "New password":      p1 = ""
        if p2      == "Confirm password":  p2 = ""

        if not entered:
            self._fp_status.config(text="Enter the OTP.", fg=ACCENT_RED); return

        # FIX: OTP expires after 10 minutes
        if time.time() - self._otp_store.get("ts", 0) > 600:
            self._fp_status.config(text="OTP expired. Request a new one.", fg=ACCENT_RED)
            return

        # FIX: Compare SHA256 of entered OTP against stored hash
        entered_hash = hashlib.sha256(entered.encode()).hexdigest()
        if entered_hash != self._otp_store.get("value"):
            self._fp_status.config(text="Incorrect OTP.", fg=ACCENT_RED); return

        ok, msg = validate_password(p1)
        if not ok:
            self._fp_status.config(text=msg, fg=ACCENT_RED); return
        if p1 != p2:
            self._fp_status.config(text="Passwords do not match.", fg=ACCENT_RED); return

        email = self._fp_email.get().strip()
        ok, msg = self.store.update_password(email, p1)
        if not ok:
            self._fp_status.config(text=msg, fg=ACCENT_RED); return

        self._otp_store = {"value": None, "ts": 0.0}
        self.logger.log("admin", "Password reset", {"email": email})
        self._fp_status.config(text="Password updated! Returning to login…", fg=BLUE2)
        self._ff.after(1300, self.show_login)


# ══════════════════════════════════════════════════════════════
#  DASHBOARD VIEW
# ══════════════════════════════════════════════════════════════
class DashboardView:
    def __init__(self, parent: tk.Frame, email: str,
                 store: AccountStore, logger: ActivityLogger, on_logout):
        self.parent    = parent
        self.email     = email
        self.store     = store
        self.logger    = logger
        self.on_logout = on_logout

        self._devices:  dict             = {}
        self._selected: str | None       = None
        self._monitor:  USBMonitor | None = None

        self._build_ui()
        self._start_monitor()

    # ── layout ────────────────────────────────────────────
    def _build_ui(self):
        self.parent.columnconfigure(1, weight=1)
        self.parent.rowconfigure(0, weight=1)
        self._build_sidebar()

        self._content = tk.Frame(self.parent, bg=BG_MID)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(1, weight=1)

        self._build_tab_bar()

        self._page_usb  = tk.Frame(self._content, bg=BG_MID)
        self._page_logs = tk.Frame(self._content, bg=BG_MID)
        self._page_mob  = tk.Frame(self._content, bg=BG_MID)

        self._build_usb_page()
        self._build_log_page()
        self._build_mobile_page()
        self._show_tab("usb")

    def _build_sidebar(self):
        sb = tk.Frame(self.parent, bg=BG_CARD, width=200)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.pack_propagate(False)

        hdr = tk.Frame(sb, bg=BLUE1)
        hdr.pack(fill="x")
        tk.Label(hdr, text="\U0001f6e1 USB Guardian",
                 bg=BLUE1, fg=TEXT_WH,
                 font=("Georgia", 12, "bold"), pady=12).pack()

        tk.Label(sb, text="Logged in as", bg=BG_CARD,
                 fg=TEXT_MT, font=F_SMALL, pady=8).pack(pady=(10, 2))
        short = (self.email[:22] + "…") if len(self.email) > 24 else self.email
        tk.Label(sb, text=short, bg=BG_CARD, fg=BLUE2,
                 font=("Courier", 9, "bold"), wraplength=180).pack(padx=8)

        separator(sb)
        sidebar_btn(sb, "Refresh Drives",  self._refresh_drives,  icon="\U0001f504")
        sidebar_btn(sb, "Reset Dashboard", self._reset_dashboard, icon="\u267b")
        sidebar_btn(sb, "Manual Allow",    self._manual_allow,    icon="\u2705")
        sidebar_btn(sb, "Full Block",      self._full_block,      icon="\U0001f6ab",
                    accent=ACCENT_RED)
        sidebar_btn(sb, "Quick Scan",      self._quick_scan,      icon="\U0001f50d")
        sidebar_btn(sb, "Open Explorer",   self._open_explorer,   icon="\U0001f4c2")

        separator(sb)
        sidebar_btn(sb, "Activity Logs",
                    lambda: self._show_tab("logs"),   icon="\U0001f4cb")
        sidebar_btn(sb, "Mobile Status",
                    lambda: self._show_tab("mobile"), icon="\U0001f4f1")

        separator(sb)
        self._sb_status_var = tk.StringVar(value="● MONITORING")
        tk.Label(sb, textvariable=self._sb_status_var,
                 bg=BG_CARD, fg=ACCENT_GRN,
                 font=("Courier", 9, "bold")).pack(pady=4)

        tk.Frame(sb, bg=BG_CARD).pack(fill="both", expand=True)
        separator(sb)
        sidebar_btn(sb, "Logout", self._logout, icon="\U0001f6aa", accent=ACCENT_RED)

    def _build_tab_bar(self):
        bar = tk.Frame(self._content, bg=BG_CARD, height=40)
        bar.grid(row=0, column=0, sticky="ew")

        self._tab_btns    = {}
        self._current_tab = ""
        for key, label in [("usb",    "LIVE USB DEVICES"),
                            ("logs",   "ACTIVITY LOGS"),
                            ("mobile", "MOBILE STATUS")]:
            btn = tk.Label(bar, text=label, bg=BG_CARD, fg=TEXT_MT,
                           font=("Courier", 9, "bold"),
                           padx=18, pady=10, cursor="hand2")
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, k=key: self._show_tab(k))
            btn.bind("<Enter>",
                     lambda e, w=btn: w.config(fg=TEXT_WH)
                     if w.cget("fg") != str(BLUE2) else None)
            btn.bind("<Leave>",
                     lambda e, w=btn, k=key:
                     w.config(fg=TEXT_MT) if self._current_tab != k else None)
            self._tab_btns[key] = btn

    def _show_tab(self, key: str):
        for k, page in [("usb",    self._page_usb),
                        ("logs",   self._page_logs),
                        ("mobile", self._page_mob)]:
            if k == key:
                page.grid(row=1, column=0, sticky="nsew")
                self._tab_btns[k].config(fg=BLUE2)
            else:
                page.grid_remove()
                self._tab_btns[k].config(fg=TEXT_MT)
        self._current_tab = key
        if key == "logs":
            self._refresh_logs()

    def _build_usb_page(self):
        p = self._page_usb
        p.columnconfigure(0, weight=1)
        p.rowconfigure(1, weight=1)

        hdr = tk.Frame(p, bg=BG_MID)
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        tk.Label(hdr, text="\U0001f50c  LIVE USB DEVICES",
                 bg=BG_MID, fg=TEXT_WH, font=F_HEAD).pack(side="left")
        self._usb_count_lbl = tk.Label(hdr, text="0 connected",
                                       bg=BG_MID, fg=TEXT_GR, font=F_SMALL)
        self._usb_count_lbl.pack(side="left", padx=14)

        main = tk.Frame(p, bg=BG_MID)
        main.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        list_card = tk.Frame(main, bg=BG_CARD)
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        tk.Label(list_card, text="Connected Devices",
                 bg=BG_CARD, fg=TEXT_GR, font=F_SMALL).pack(
                     anchor="w", padx=12, pady=(10, 4))

        self._usb_listbox = tk.Listbox(
            list_card, bg=BG_FIELD, fg=TEXT_WH,
            font=("Courier New", 10), relief="flat", bd=0,
            selectbackground=BLUE1, selectforeground=TEXT_WH,
            activestyle="none", highlightthickness=0, height=8
        )
        self._usb_listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._usb_listbox.bind("<<ListboxSelect>>", self._on_device_select)

        self._usb_empty_lbl = tk.Label(
            list_card,
            text="\U0001f4e6  No USB Devices Connected\n\n"
                 "Insert a USB drive\nto begin monitoring",
            bg=BG_CARD, fg=TEXT_MT, font=("Courier", 10), justify="center"
        )
        self._usb_empty_lbl.pack(expand=True)

        detail_card = tk.Frame(main, bg=BG_CARD)
        detail_card.grid(row=0, column=1, sticky="nsew")
        detail_card.columnconfigure(0, weight=1)

        tk.Label(detail_card, text="Device Details",
                 bg=BG_CARD, fg=TEXT_GR, font=F_SMALL).pack(
                     anchor="w", padx=12, pady=(10, 4))

        self._detail_name   = self._detail_row(detail_card, "Name",   "—")
        self._detail_path   = self._detail_row(detail_card, "Path",   "—")
        self._detail_size   = self._detail_row(detail_card, "Size",   "—")
        self._detail_time   = self._detail_row(detail_card, "Seen",   "—")
        self._detail_status = self._detail_row(detail_card, "Status", "—")

        separator(detail_card, BORDER)

        act = tk.Frame(detail_card, bg=BG_CARD)
        act.pack(fill="x", padx=12, pady=6)

        make_gradient_btn(act, "\u2705 ALLOW", self._allow_device,
                          w=140, h=34, bg=BG_CARD).pack(side="left", padx=(0, 6))

        block_btn = tk.Canvas(act, width=140, height=34, bg=BG_CARD,
                              highlightthickness=0, cursor="hand2")
        block_btn.pack(side="left")
        gradient_rect(block_btn, 0, 0, 140, 34, "#c0392b", ACCENT_RED)
        block_btn.create_text(70, 17, text="\U0001f6ab BLOCK",
                              fill="white", font=("Georgia", 10, "bold"))
        block_btn.bind("<Button-1>", lambda e: self._block_device())
        block_btn.bind("<Enter>", lambda e: (
            block_btn.delete("all"),
            gradient_rect(block_btn, 0, 0, 140, 34, "#922b21", "#e74c3c"),
            block_btn.create_text(70, 17, text="\U0001f6ab BLOCK →",
                                  fill="white", font=("Georgia", 10, "bold"))
        ))
        block_btn.bind("<Leave>", lambda e: (
            block_btn.delete("all"),
            gradient_rect(block_btn, 0, 0, 140, 34, "#c0392b", ACCENT_RED),
            block_btn.create_text(70, 17, text="\U0001f6ab BLOCK",
                                  fill="white", font=("Georgia", 10, "bold"))
        ))

        separator(detail_card, BORDER)

        self._scan_frame  = tk.Frame(detail_card, bg=BG_CARD)
        self._scan_frame.pack(fill="x", padx=12, pady=4)
        self._scan_result = tk.Label(
            self._scan_frame, text="",
            bg=BG_CARD, fg=TEXT_GR, font=F_SMALL, wraplength=200, justify="left"
        )
        self._scan_result.pack(anchor="w")

        make_gradient_btn(
            detail_card, "\U0001f50d Quick Scan",
            self._quick_scan, w=180, h=32, bg=BG_CARD
        ).pack(padx=12, pady=6)

    def _detail_row(self, parent, label, value) -> tk.Label:
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(fill="x", padx=12, pady=2)
        tk.Label(row, text=f"{label}:", bg=BG_CARD, fg=TEXT_MT,
                 font=F_SMALL, width=7, anchor="w").pack(side="left")
        val = tk.Label(row, text=value, bg=BG_CARD, fg=TEXT_WH,
                       font=F_SMALL, anchor="w")
        val.pack(side="left")
        return val

    def _build_log_page(self):
        p = self._page_logs
        p.columnconfigure(0, weight=1)
        p.columnconfigure(1, weight=1)
        p.rowconfigure(1, weight=1)

        tk.Label(p, text="\U0001f4cb  ACTIVITY LOGS",
                 bg=BG_MID, fg=TEXT_WH, font=F_HEAD).grid(
                     row=0, column=0, columnspan=2,
                     sticky="w", padx=20, pady=(16, 8))

        atk_card = tk.Frame(p, bg=BG_CARD)
        atk_card.grid(row=1, column=0, sticky="nsew", padx=(20, 8), pady=(0, 16))
        atk_card.rowconfigure(1, weight=1)
        atk_card.columnconfigure(0, weight=1)

        hdr = tk.Frame(atk_card, bg="#2c1010")
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="\u26a0  ATTACKER ACTIVITY",
                 bg="#2c1010", fg=ACCENT_RED,
                 font=("Courier", 10, "bold"), pady=8).pack(side="left", padx=10)

        self._atk_text = self._log_text_widget(atk_card, row=1)

        tk.Label(atk_card, text="Captured Photos",
                 bg=BG_CARD, fg=TEXT_MT, font=F_SMALL).grid(
                     row=2, column=0, sticky="w", padx=10, pady=(4, 2))
        gallery_scroll = tk.Frame(atk_card, bg=BG_CARD)
        gallery_scroll.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        self._gallery = gallery_scroll

        adm_card = tk.Frame(p, bg=BG_CARD)
        adm_card.grid(row=1, column=1, sticky="nsew", padx=(0, 20), pady=(0, 16))
        adm_card.rowconfigure(1, weight=1)
        adm_card.columnconfigure(0, weight=1)

        hdr2 = tk.Frame(adm_card, bg="#0d1f10")
        hdr2.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr2, text="\U0001f4bc  ADMIN ACTIVITY",
                 bg="#0d1f10", fg=ACCENT_GRN,
                 font=("Courier", 10, "bold"), pady=8).pack(side="left", padx=10)

        self._adm_text = self._log_text_widget(adm_card, row=1)

        clr = tk.Label(p, text="Clear All Logs", bg=BG_MID, fg=TEXT_MT,
                       font=(F_SMALL[0], F_SMALL[1], "underline"), cursor="hand2")
        clr.grid(row=2, column=0, columnspan=2, pady=(0, 6))
        clr.bind("<Enter>",    lambda e: clr.config(fg=ACCENT_RED))
        clr.bind("<Leave>",    lambda e: clr.config(fg=TEXT_MT))
        clr.bind("<Button-1>", lambda e: self._clear_logs())

    def _log_text_widget(self, parent, row) -> tk.Text:
        frame = tk.Frame(parent, bg=BG_FIELD)
        frame.grid(row=row, column=0, sticky="nsew", padx=8, pady=(0, 6))
        sb  = tk.Scrollbar(frame)
        sb.pack(side="right", fill="y")
        txt = tk.Text(frame, bg=BG_FIELD, fg=TEXT_GR, font=F_MONO,
                      relief="flat", bd=0, wrap="word",
                      yscrollcommand=sb.set, state="disabled",
                      highlightthickness=0, padx=8, pady=6)
        txt.pack(fill="both", expand=True)
        sb.config(command=txt.yview)
        return txt

    def _build_mobile_page(self):
        p = self._page_mob
        p.columnconfigure(0, weight=1)

        tk.Label(p, text="\U0001f4f1  MOBILE STATUS",
                 bg=BG_MID, fg=TEXT_WH, font=F_HEAD).pack(
                     anchor="w", padx=20, pady=(16, 8))

        card = tk.Frame(p, bg=BG_CARD)
        card.pack(fill="x", padx=20, pady=8)

        tk.Label(card, text="Mobile integration is not yet active.",
                 bg=BG_CARD, fg=TEXT_GR, font=F_BODY, pady=16).pack()
        tk.Label(card,
                 text="Future versions will push real-time alerts\n"
                      "to a companion mobile app via the cloud API.",
                 bg=BG_CARD, fg=TEXT_MT, font=F_SMALL).pack(pady=(0, 16))

        for label, val in [("Notification Push", "Simulated"),
                            ("Last Alert Sent",   "—"),
                            ("Registered Device", "None"),
                            ("Alert Email",       self.email)]:
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill="x", padx=16, pady=3)
            tk.Label(row, text=f"{label}:", bg=BG_CARD, fg=TEXT_MT,
                     font=F_SMALL, width=20, anchor="w").pack(side="left")
            tk.Label(row, text=val, bg=BG_CARD, fg=TEXT_WH,
                     font=F_SMALL).pack(side="left")

    # ── monitor ───────────────────────────────────────────
    def _start_monitor(self):
        root = self.parent.winfo_toplevel()
        self._monitor = USBMonitor(
            root=root,
            on_connect=self._on_usb_connect,
            on_disconnect=self._on_usb_disconnect,
        )
        self._monitor.start()

    def _refresh_drives(self):
        def _scan():
            root = self.parent.winfo_toplevel()
            tmp  = USBMonitor(root=root, on_connect=lambda d: None,
                              on_disconnect=lambda p: None)
            drives = tmp.get_usb_drives()
            self.parent.after(0, lambda: self._apply_drives(drives))
        threading.Thread(target=_scan, daemon=True, name="DriveRefresh").start()

    def _apply_drives(self, drives: list):
        current_paths = {d["path"] for d in drives}
        for path in list(self._devices.keys()):
            if path not in current_paths:
                del self._devices[path]
        for d in drives:
            if d["path"] not in self._devices:
                self._devices[d["path"]] = {
                    "info":   d,
                    "status": "connected",
                    "seen":   now_str(),
                }
        self._update_usb_list()
        self.logger.log("admin", "Manual drive refresh",
                        {"count": len(self._devices)})

    def _on_usb_connect(self, device: dict):
        path = device["path"]
        self._devices[path] = {
            "info":   device,
            "status": "blocked",
            "seen":   now_str(),
        }
        self._update_usb_list()
        self._sb_status_var.set("⚠  USB DETECTED")
        self.parent.after(4000, lambda: self._sb_status_var.set("● MONITORING"))

        # FIX: email + camera in background thread; triggered on every USB insert
        def _alert():
            photo_path = CameraService.capture()
            # FIX: send_usb_alert always called on USB insert
            ok, msg = EmailService.send_usb_alert(
                self.email, device["name"], photo_path
            )
            if ok:
                print(f"[EMAIL SENT] USB insert alert delivered for {device['name']}")
            else:
                print(f"[EMAIL FAILED] USB insert alert failed: {msg}")

            self.logger.log(
                "attacker", "USB device inserted",
                {"device":     device["name"],
                 "path":       path,
                 "photo":      photo_path or "none",
                 "alert_sent": ok}
            )
            firebase_push("devices", {
                "email":  self.email,
                "device": device["name"],
                "path":   path,
                "time":   now_str(),
                "status": "blocked",
            })

      
            # 🔥 LIVE NOTIFICATION TRIGGER
        firebase_push("notifications", {
            "title": "USB Alert ⚠",
            "message": f"USB Connected: {device['name']}",
            "time": now_str()
            })
        threading.Thread(target=_alert, daemon=True, name="USBAlert").start()

    def _on_usb_disconnect(self, path: str):
        name = self._devices.get(path, {}).get("info", {}).get("name", path)
        self._devices.pop(path, None)
        if self._selected == path:
            self._selected = None
        self._update_usb_list()
        self.logger.log("attacker", "USB device removed",
                        {"device": name, "path": path})

    def _update_usb_list(self):
        self._usb_listbox.delete(0, "end")
        for path, data in self._devices.items():
            info   = data["info"]
            status = data["status"]
            badge  = "✓" if status == "allowed" else "✗" if status == "blocked" else "◉"
            self._usb_listbox.insert(
                "end",
                f"  {badge}  {info['name']}  ({info.get('size_gb', '?')} GB)"
            )
        count = len(self._devices)
        self._usb_count_lbl.config(text=f"{count} connected")

        if count == 0:
            self._usb_listbox.pack_forget()
            self._usb_empty_lbl.pack(expand=True)
        else:
            self._usb_empty_lbl.pack_forget()
            self._usb_listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _on_device_select(self, event):
        sel = self._usb_listbox.curselection()
        if not sel:
            return
        idx   = sel[0]
        paths = list(self._devices.keys())
        if idx >= len(paths):
            return
        self._selected = paths[idx]
        data   = self._devices[self._selected]
        info   = data["info"]
        self._detail_name.config(text=info.get("name", "—"))
        self._detail_path.config(text=self._selected)
        self._detail_size.config(text=f"{info.get('size_gb', '?')} GB")
        self._detail_time.config(text=data.get("seen", "—"))
        status = data.get("status", "—")
        color  = (ACCENT_GRN if status == "allowed"
                  else ACCENT_RED if status == "blocked"
                  else ACCENT_YLW)
        self._detail_status.config(text=status.upper(), fg=color)
        self._scan_result.config(text="")

    # ── USB actions ───────────────────────────────────────
    def _allow_device(self):
        if not self._selected or self._selected not in self._devices:
            messagebox.showinfo("Allow", "Select a device first.")
            return

        path = self._selected

        if not is_admin():
            proceed = messagebox.askyesno(
                "Privilege Warning",
                "Not running as Administrator.\n"
                "Unblocking may be incomplete.\n\nContinue anyway?"
            )
            if not proceed:
                return

        pw = simpledialog.askstring(
            "Authentication Required",
            "Enter your password to allow this device:",
            show="*"
        )
        if not pw:
            return

        if not self.store.verify(self.email, pw):
            messagebox.showerror("Authentication Failed", "Incorrect password.")
            self.logger.log("attacker", "Failed allow authentication",
                            {"email": self.email, "path": path})
            return

        def _do_unblock():
            ok, msg = USBBlocker.unblock(path)
            def _update():
                if path in self._devices:
                    self._devices[path]["status"] = "allowed"
                self._update_usb_list()
                if self._selected == path:
                    self._detail_status.config(text="ALLOWED", fg=ACCENT_GRN)
                self.logger.log("admin", "Device allowed",
                                {"path": path, "email": self.email})
                self.parent.after(10_000, lambda: self._auto_reblock(path))
            self.parent.after(0, _update)

        threading.Thread(target=_do_unblock, daemon=True, name="UnblockDevice").start()

    def _auto_reblock(self, path: str):
        if path in self._devices and self._devices[path]["status"] == "allowed":
            threading.Thread(
                target=lambda: USBBlocker.block(path),
                daemon=True, name="AutoReblock"
            ).start()
            self._devices[path]["status"] = "blocked"
            self._update_usb_list()
            self.logger.log("admin", "Auto-reblock applied", {"path": path})

    def _block_device(self):
        if not self._selected or self._selected not in self._devices:
            messagebox.showinfo("Block", "Select a device first.")
            return

        info = self._devices[self._selected]["info"]
        path = self._selected

        if not is_admin():
            messagebox.showwarning(
                "Privilege Warning",
                "Not running as Administrator.\n"
                "OS-level block may be incomplete."
            )

        def _do_block():
            ok, msg = USBBlocker.block(path)
            def _update():
                if path in self._devices:
                    self._devices[path]["status"] = "blocked"
                self._update_usb_list()
                if self._selected == path:
                    self._detail_status.config(text="BLOCKED", fg=ACCENT_RED)
                self.logger.log(
                    "attacker", "Device manually blocked",
                    {"device": info["name"], "path": path,
                     "os_block_ok": ok, "os_msg": msg}
                )
                messagebox.showwarning(
                    "Device Blocked",
                    f"'{info['name']}' has been blocked.\n"
                    f"OS result: {'Success' if ok else 'Warning – see console'}"
                )
            self.parent.after(0, _update)

        threading.Thread(target=_do_block, daemon=True, name="BlockDevice").start()

    def _manual_allow(self):
        self._allow_device()

    def _full_block(self):
        if not self._devices:
            messagebox.showinfo("Full Block", "No USB devices connected.")
            return

        paths = list(self._devices.keys())

        def _do_full_block():
            results = []
            for p in paths:
                ok, msg = USBBlocker.block(p)
                name = self._devices.get(p, {}).get("info", {}).get("name", p)
                results.append(f"{name}: {'OK' if ok else 'FAILED'}")

            def _update():
                for p in paths:
                    if p in self._devices:
                        self._devices[p]["status"] = "blocked"
                self._update_usb_list()
                self.logger.log("admin", "FULL BLOCK engaged",
                                {"count": len(paths), "results": results})
                messagebox.showwarning(
                    "Full Block",
                    f"All {len(paths)} USB device(s) blocked.\n\n"
                    + "\n".join(results)
                )
            self.parent.after(0, _update)

        threading.Thread(target=_do_full_block, daemon=True, name="FullBlock").start()

    def _quick_scan(self):
        """
        FIX: Scan runs in background thread.
        FIX: Malware alert email triggered here via send_malware_alert().
        FIX: Uses structured dict results from updated MalwareScanner.
        """
        if not self._selected or self._selected not in self._devices:
            messagebox.showinfo("Scan", "Select a device first.")
            return

        info = self._devices[self._selected]["info"]
        path = self._selected
        self._scan_result.config(text="Scanning…", fg=TEXT_GR)

        def _do_scan():
            # FIX: MalwareScanner.scan() now returns list[dict], not list[str]
            clean, found = MalwareScanner.scan(path)

            def _update():
                if clean:
                    self._scan_result.config(
                        text="\u2705 No suspicious files found.", fg=ACCENT_GRN
                    )
                    self.logger.log("admin", "Scan clean",
                                    {"device": info["name"], "path": path})
                else:
                    # FIX: Build preview from structured dicts
                    preview_lines = []
                    for item in found[:3]:
                        preview_lines.append(
                            f"{Path(item['path']).name} [{item['reason']}]"
                        )
                    preview = "\n".join(preview_lines)
                    self._scan_result.config(
                        text=f"\u26a0 {len(found)} threat(s)!\n{preview}",
                        fg=ACCENT_RED
                    )

                    USBBlocker.block(path)
                    if path in self._devices:
                        self._devices[path]["status"] = "blocked"
                    self._update_usb_list()

                    # FIX: Log with structured data
                    file_paths = [item["path"] for item in found]
                    self.logger.log(
                        "attacker", "Malware detected",
                        {"device": info["name"],
                         "path":   path,
                         "count":  len(found),
                         "files":  file_paths[:10]}
                    )

                    # FIX: Send malware-specific alert email
                    def _send_malware_email():
                        photo_path = CameraService.capture()
                        ok, msg = EmailService.send_malware_alert(
                            self.email, info["name"], file_paths, photo_path
                        )
                        if ok:
                            print(f"[EMAIL SENT] Malware alert delivered for {info['name']}")
                        else:
                            print(f"[EMAIL FAILED] Malware alert failed: {msg}")

                    threading.Thread(
                        target=_send_malware_email,
                        daemon=True, name="MalwareAlertEmail"
                    ).start()

                    messagebox.showerror(
                        "Malware Alert",
                        f"{len(found)} suspicious file(s) found on '{info['name']}'!\n"
                        "Device blocked. Alert email sent.\n\n"
                        + MalwareScanner.format_report(found[:5])
                    )
            self.parent.after(0, _update)

        threading.Thread(target=_do_scan, daemon=True, name="QuickScan").start()

    def _open_explorer(self):
        if not self._selected or self._selected not in self._devices:
            messagebox.showinfo("Explorer", "Select a device first.")
            return

        path   = self._selected
        status = self._devices[path]["status"]
        if status == "blocked":
            messagebox.showerror("Blocked", "This device is blocked. Allow it first.")
            return

        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            self.logger.log("admin", "Explorer opened", {"path": path})
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _reset_dashboard(self):
        try:
            self._devices.clear()
            self._selected = None
            self._usb_listbox.delete(0, tk.END)
            self._usb_count_lbl.config(text="0 connected")
            if self._monitor:
                self._monitor.stop()
                time.sleep(0.3)
                self._start_monitor()
            self.logger.log("admin", "Dashboard reset", {"user": self.email})
            messagebox.showinfo("Reset", "Dashboard reset successful.")
        except Exception as exc:
            print(f"[RESET ERROR] {exc}")
            messagebox.showerror("Error", "Reset failed.")

    # ── log helpers ───────────────────────────────────────
    def _refresh_logs(self):
        self._render_log(self._atk_text, self.logger.get_by_kind("attacker"))
        self._render_log(self._adm_text, self.logger.get_by_kind("admin"))
        self._refresh_gallery()

    def _render_log(self, widget: tk.Text, events: list):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        if not events:
            widget.insert("end", "No events yet.\n", "muted")
        else:
            widget.tag_config("ts",     foreground=TEXT_MT)
            widget.tag_config("event",  foreground=TEXT_WH)
            widget.tag_config("detail", foreground=TEXT_GR)
            widget.tag_config("muted",  foreground=TEXT_MT)
            for e in events:
                widget.insert("end", f"[{e['ts']}]  ", "ts")
                widget.insert("end", f"{e['event']}\n", "event")
                for k, v in e.items():
                    if k not in ("ts", "kind", "event"):
                        widget.insert("end", f"    {k}: {v}\n", "detail")
        widget.config(state="disabled")

    def _refresh_gallery(self):
        for w in self._gallery.winfo_children():
            w.destroy()

        photos = sorted(PHOTO_DIR.glob("*.jpg")) + sorted(PHOTO_DIR.glob("*.png"))
        if not photos:
            tk.Label(self._gallery, text="No captures yet",
                     bg=BG_CARD, fg=TEXT_MT, font=F_SMALL).pack(side="left")
            return

        if PIL_AVAILABLE:
            for ph in photos[-6:]:
                try:
                    img   = Image.open(ph).resize((60, 45))
                    imgtk = ImageTk.PhotoImage(img)
                    lbl   = tk.Label(self._gallery, image=imgtk,
                                     bg=BG_CARD, cursor="hand2",
                                     relief="flat", bd=2)
                    lbl.image = imgtk
                    lbl.pack(side="left", padx=3)
                    lbl.bind("<Button-1>",
                             lambda e, p=str(ph): self._view_photo(p))
                except Exception as exc:
                    print(f"[GALLERY] Could not load {ph}: {exc}")
        else:
            tk.Label(self._gallery,
                     text=f"{len(photos)} capture(s) – install Pillow to preview",
                     bg=BG_CARD, fg=TEXT_MT, font=F_SMALL).pack(side="left")

    def _view_photo(self, path: str):
        if not PIL_AVAILABLE:
            messagebox.showinfo("Pillow Required",
                                "Install Pillow to preview captured photos.")
            return
        win = tk.Toplevel()
        win.title("Captured Photo")
        win.configure(bg=BG_DARK)
        try:
            img   = Image.open(path).resize((480, 360))
            imgtk = ImageTk.PhotoImage(img)
            lbl   = tk.Label(win, image=imgtk, bg=BG_DARK)
            lbl.image = imgtk
            lbl.pack(padx=20, pady=20)
        except Exception as exc:
            tk.Label(win, text=f"Cannot display image:\n{exc}",
                     bg=BG_DARK, fg=TEXT_WH).pack(padx=20, pady=20)

    def _clear_logs(self):
        if messagebox.askyesno("Clear Logs",
                               "Delete all activity logs? This cannot be undone."):
            self.logger.clear()
            self._refresh_logs()

    def _logout(self):
        if self._monitor:
            self._monitor.stop()
        self.logger.log("admin", "User logged out", {"email": self.email})
        self.on_logout()

    def destroy(self):
        if self._monitor:
            try:
                self._monitor.stop()
            except Exception:
                pass
        for w in self.parent.winfo_children():
            w.destroy()


# ══════════════════════════════════════════════════════════════
#  APP CONTROLLER
# ══════════════════════════════════════════════════════════════
class AppController:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        self.root.resizable(True, True)
        self.root.configure(bg=BG_DARK)
        self._center_window()

        self.store   = AccountStore()
        self.logger  = ActivityLogger()
        self.limiter = RateLimiter()

        self._container = tk.Frame(self.root, bg=BG_DARK)
        self._container.pack(fill="both", expand=True)

        self._auth_view: AuthView | None      = None
        self._dash_view: DashboardView | None = None

        if not is_admin():
            print("[STARTUP] WARNING: Not running as Administrator. "
                  "OS-level USB blocking will be limited. "
                  "Right-click → 'Run as administrator' for full protection.")

        self._show_auth()

    def _show_auth(self):
        for w in self._container.winfo_children():
            w.destroy()
        self._dash_view = None

        split = tk.Frame(self._container, bg=BG_DARK)
        split.pack(fill="both", expand=True)

        left  = tk.Frame(split, bg=BG_DARK, width=WIN_W // 2)
        right = tk.Frame(split, bg=BG_MID)
        left.pack(side="left",  fill="both", expand=True)
        right.pack(side="right", fill="both", expand=True)
        right.pack_propagate(False)

        self._draw_auth_illustration(left)

        self._auth_view = AuthView(
            parent     = right,
            store      = self.store,
            logger     = self.logger,
            limiter    = self.limiter,
            on_success = self._on_login_success,
        )

    def _on_login_success(self, email: str):
        for w in self._container.winfo_children():
            w.destroy()
        self._auth_view = None

        dash_frame = tk.Frame(self._container, bg=BG_MID)
        dash_frame.pack(fill="both", expand=True)

        self._dash_view = DashboardView(
            parent    = dash_frame,
            email     = email,
            store     = self.store,
            logger    = self.logger,
            on_logout = self._show_auth,
        )

    def _draw_auth_illustration(self, parent: tk.Frame):
        c = tk.Canvas(parent, bg=BG_DARK, highlightthickness=0)
        c.pack(fill="both", expand=True)

        W = WIN_W // 2
        H = WIN_H

        for i in range(18, 0, -1):
            alpha = int(255 * (i / 18) * 0.08)
            col   = f"#1a{alpha:02x}6e" if i > 9 else f"#0d1a{alpha:02x}"
            try:
                c.create_oval(
                    W // 2 - i * 18, H // 2 - i * 18,
                    W // 2 + i * 18, H // 2 + i * 18,
                    fill="", outline=col, width=2
                )
            except Exception:
                pass

        shield_pts = [
            W // 2,      H // 2 - 110,
            W // 2 + 70, H // 2 - 70,
            W // 2 + 80, H // 2 + 10,
            W // 2,      H // 2 + 80,
            W // 2 - 80, H // 2 + 10,
            W // 2 - 70, H // 2 - 70,
        ]
        c.create_polygon(shield_pts, fill=ACCENT_DARK, outline=BLUE1,
                         width=2, smooth=False)

        cx, cy = W // 2, H // 2
        c.create_rectangle(cx - 22, cy - 8, cx + 22, cy + 28, fill=BLUE1, outline="")
        c.create_arc(cx - 18, cy - 32, cx + + 18, cy - 4,
                     start=0, extent=180, fill="", outline=BLUE2, width=3)
        c.create_oval(cx - 7, cy + 2, cx + 7, cy + 16, fill=BG_DARK, outline="")

        c.create_text(W // 2, H // 2 + 115,
                      text="\U0001f6e1  USB GUARDIAN",
                      fill=TEXT_WH, font=("Georgia", 15, "bold"))
        c.create_text(W // 2, H // 2 + 140,
                      text="Real-time USB Security Platform",
                      fill=TEXT_GR, font=("Courier", 9))

        for px, py, col in [(W * 0.15, H * 0.2,  BLUE1),
                             (W * 0.8,  H * 0.15, BLUE2),
                             (W * 0.1,  H * 0.75, BLUE2),
                             (W * 0.85, H * 0.8,  BLUE1),
                             (W * 0.5,  H * 0.1,  BLUE1)]:
            c.create_oval(px - 4, py - 4, px + 4, py + 4, fill=col, outline="")

    def _center_window(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(
            f"{WIN_W}x{WIN_H}+{(sw - WIN_W) // 2}+{(sh - WIN_H) // 2}"
        )

    def run(self):
        self.root.mainloop()


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    AppController().run()