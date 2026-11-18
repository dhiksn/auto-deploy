#!/usr/bin/env python3
"""
AutoDeploy AI  ·  Git Init · AI Commit · Auto Push

Requires:  pip install rich prompt_toolkit
"""

# ── Standard library ──────────────────────────────────────────────────────────
import os
import re
import sys
import json
import subprocess
import time
import threading
from contextlib import contextmanager
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

# Fix UnicodeEncodeError di Windows terminal
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Auto-install dependencies ─────────────────────────────────────────────────
def _ensure(pkg: str, import_as: str | None = None):
    import importlib
    name = import_as or pkg
    try:
        return importlib.import_module(name)
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pkg, "-q"],
            stdout=subprocess.DEVNULL,
        )
        return importlib.import_module(name)

_ensure("rich")
_ensure("prompt_toolkit", "prompt_toolkit")

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.markup import escape
from rich.padding import Padding
from rich.panel import Panel
from rich.spinner import Spinner
from rich.style import Style
from rich.table import Table
from rich.text import Text
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.formatted_text import HTML

# ── Console ───────────────────────────────────────────────────────────────────
console = Console(highlight=False)

APP_VERSION = "1.8.7"

# ── Theme: teal → emerald → lime, amber untuk warning (no purple, no blue) ────
C_ACCENT = "#2dd4bf"   # teal-400
C_HEAD   = f"bold {C_ACCENT}"
C_TEXT   = "#f3f4f6"   # gray-100
C_VAL    = "#e5e7eb"   # gray-200
C_LABEL  = "#9ca3af"   # gray-400
C_DIM    = "#6b7280"   # gray-500
C_LINE   = "#4b5563"   # gray-600
C_OK     = "#34d399"   # emerald-400
C_WARN   = "#fbbf24"   # amber-400
C_ERR    = "#f87171"   # red-400
C_CHIP   = "#1f2937"   # gray-800 — latar chip / keycap
C_INK    = "#0b0f14"   # teks gelap di atas badge berwarna

BRAND_GRADIENT = ("#5eead4", "#2dd4bf", "#34d399", "#a3e635")

PT_STYLE = PTStyle.from_dict({
    "arrow":       f"{C_ACCENT} bold",
    "label":       C_TEXT,
    "placeholder": C_DIM,
    "":            C_TEXT,
})

# ── Load .env ─────────────────────────────────────────────────────────────────
def _parse_env_file(path: Path):
    """Parse dan load satu file .env ke os.environ."""
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


def _get_config_path() -> Path:
    """
    Lokasi config file:
    - Windows : C:\\ProgramData\\autodeploy\\config.env
    - Linux/Mac: ~/.autodeploy.env
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData"))
        config_dir = base / "autodeploy"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.env"
    return Path.home() / ".autodeploy.env"


def load_env():
    # 1. Config global per platform
    _parse_env_file(_get_config_path())
    # 2. .env di folder script (untuk development lokal)
    _parse_env_file(Path(__file__).parent / ".env")
    # 3. .env di current working directory — override semua
    _parse_env_file(Path.cwd() / ".env")


load_env()

# ── Config ────────────────────────────────────────────────────────────────────
AI_PROVIDER        = os.environ.get("AI_PROVIDER", "openrouter")
OPENAI_KEY         = os.environ.get("OPENAI_API_KEY", "")
GROQ_KEY              = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_KEY        = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL      = os.environ.get("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_API_TOKEN  = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_MODEL      = os.environ.get("CLOUDFLARE_MODEL", "@cf/meta/llama-4-scout-17b-16e-instruct")
OLLAMA_URL            = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL          = os.environ.get("OLLAMA_MODEL", "llama3")
OPENAI_MODEL          = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
GROQ_MODEL            = os.environ.get("GROQ_MODEL", "llama3-8b-8192")
DEFAULT_BRANCH        = os.environ.get("DEFAULT_BRANCH", "main")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SETUP WIZARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ENV_PATH = _get_config_path()

def is_configured() -> bool:
    """Cek apakah sudah ada konfigurasi AI yang valid."""
    provider = os.environ.get("AI_PROVIDER", "")
    if not provider:
        return False
    if provider == "groq" and not os.environ.get("GROQ_API_KEY", ""):
        return False
    if provider == "openai" and not os.environ.get("OPENAI_API_KEY", ""):
        return False
    if provider == "openrouter" and not os.environ.get("OPENROUTER_API_KEY", ""):
        return False
    if provider == "cloudflare" and (
        not os.environ.get("CLOUDFLARE_ACCOUNT_ID", "") or
        not os.environ.get("CLOUDFLARE_API_TOKEN", "")
    ):
        return False
    # ollama tidak butuh API key
    return True


PROVIDERS = [
    # id,          nama,         tier,    keterangan,               situs
    ("openrouter", "OpenRouter", "FREE",  "20+ model gratis",       "openrouter.ai"),
    ("cloudflare", "Cloudflare", "FREE",  "Workers AI",             "dash.cloudflare.com"),
    ("groq",       "Groq",       "FREE",  "gratis, sangat cepat",   "console.groq.com/keys"),
    ("ollama",     "Ollama",     "LOCAL", "offline, tanpa API key", "ollama.com"),
    ("openai",     "OpenAI",     "PAID",  "berbayar",               "platform.openai.com/api-keys"),
]
_TIER_COLORS = {"FREE": C_OK, "LOCAL": C_ACCENT, "PAID": C_WARN}


def _provider_table() -> Table:
    t = Table.grid(padding=(0, 2))
    t.add_column(justify="right", style=C_DIM, no_wrap=True)
    t.add_column(no_wrap=True)
    t.add_column(no_wrap=True)
    t.add_column(style=C_LABEL, no_wrap=True)
    t.add_column(style=C_DIM, overflow="fold")
    for i, (_, name, tier, note, site) in enumerate(PROVIDERS, 1):
        t.add_row(str(i), Text(name, style=f"bold {C_TEXT}"), badge(tier, _TIER_COLORS[tier]), note, site)
    return t


def run_setup_wizard():
    """Setup wizard interaktif untuk konfigurasi pertama kali."""
    ui_clear()
    ui_banner()

    console.print(card(
        Text.from_markup(
            f"[bold {C_TEXT}]Selamat datang di AutoDeploy AI![/]\n\n"
            f"[{C_LABEL}]Sepertinya ini pertama kali kamu menjalankan [/][{C_ACCENT}]autodeploy[/][{C_LABEL}].\n"
            f"Setup ini hanya perlu dilakukan sekali.\n"
            f"Konfigurasi akan disimpan di [/][{C_ACCENT}]{escape(str(_get_config_path()))}[/]"
        ),
        "First-time setup", tone="accent",
    ))
    console.print()

    # ── Pilih provider ────────────────────────────────────────────────────────
    console.print(card(_provider_table(), "Pilih AI provider"))
    console.print()

    while True:
        choice = ask("Provider (1/2/3/4/5)")
        if choice in {"1", "2", "3", "4", "5"}:
            provider = PROVIDERS[int(choice) - 1][0]
            break
        ui_warn("Masukkan 1, 2, 3, 4, atau 5.")

    config_lines = [f"AI_PROVIDER={provider}"]

    # ── API key OpenRouter ────────────────────────────────────────────────────
    if provider == "openrouter":
        console.print()
        console.print(hint(
            f"[{C_LABEL}]Daftar gratis di [/][{C_ACCENT}]https://openrouter.ai[/]\n"
            f"[{C_LABEL}]Klik [/][{C_ACCENT}]Keys[/][{C_LABEL}] → [/][{C_ACCENT}]Create Key[/][{C_LABEL}] → paste di bawah.[/]"
        ))
        console.print()
        while True:
            key = ask("OpenRouter API Key", "sk-or-...")
            if key.startswith("sk-or-") and len(key) > 20:
                break
            ui_warn("API key tidak valid. Harus diawali 'sk-or-'.")
        config_lines += [
            f"OPENROUTER_API_KEY={key}",
            "OPENROUTER_MODEL=google/gemma-4-31b-it:free",
        ]

    # ── API key Cloudflare ────────────────────────────────────────────────────
    elif provider == "cloudflare":
        console.print()
        console.print(hint(
            f"[{C_LABEL}]Daftar gratis di [/][{C_ACCENT}]https://dash.cloudflare.com[/]\n"
            f"[{C_LABEL}]Account ID ada di sidebar kanan dashboard.\n"
            f"API Token: Profile → API Tokens → Create Token → Workers AI template.[/]"
        ))
        console.print()
        while True:
            account_id = ask("Account ID", "01b402d8ebd6d105b6dd06a792a704b7")
            if len(account_id) >= 32:
                break
            ui_warn("Account ID tidak valid.")
        while True:
            cf_token = ask("API Token", "cfut_...")
            if len(cf_token) > 20:
                break
            ui_warn("API Token tidak valid.")
        console.print()
        console.print(hint(
            f"[{C_LABEL}]Model default: [/][{C_ACCENT}]@cf/meta/llama-4-scout-17b-16e-instruct[/]\n"
            f"[{C_LABEL}]Model lain tersedia di [/][{C_ACCENT}]https://developers.cloudflare.com/workers-ai/models/[/]\n"
            f"[{C_LABEL}]Tekan Enter untuk pakai default.[/]"
        ))
        console.print()
        cf_model = ask("Model", "@cf/meta/llama-4-scout-17b-16e-instruct")
        cf_model = cf_model or "@cf/meta/llama-4-scout-17b-16e-instruct"
        config_lines += [
            f"CLOUDFLARE_ACCOUNT_ID={account_id}",
            f"CLOUDFLARE_API_TOKEN={cf_token}",
            f"CLOUDFLARE_MODEL={cf_model}",
        ]

    # ── API key Groq ──────────────────────────────────────────────────────────
    elif provider == "groq":
        console.print()
        console.print(hint(
            f"[{C_LABEL}]Daftar gratis di [/][{C_ACCENT}]https://console.groq.com/keys[/]\n"
            f"[{C_LABEL}]lalu buat API key baru dan paste di bawah.[/]"
        ))
        console.print()
        while True:
            key = ask("Groq API Key", "gsk_...")
            if key.startswith("gsk_") and len(key) > 20:
                break
            ui_warn("API key tidak valid. Harus diawali 'gsk_'.")
        config_lines += [
            f"GROQ_API_KEY={key}",
            "GROQ_MODEL=llama-3.1-8b-instant",
        ]

    elif provider == "openai":
        console.print()
        console.print(hint(
            f"[{C_LABEL}]Dapatkan API key di [/][{C_ACCENT}]https://platform.openai.com/api-keys[/]"
        ))
        console.print()
        while True:
            key = ask("OpenAI API Key", "sk-...")
            if key.startswith("sk-") and len(key) > 20:
                break
            ui_warn("API key tidak valid. Harus diawali 'sk-'.")
        config_lines += [
            f"OPENAI_API_KEY={key}",
            "OPENAI_MODEL=gpt-4o-mini",
        ]

    elif provider == "ollama":
        console.print()
        console.print(card(
            Text.from_markup(
                f"[{C_LABEL}]Pastikan Ollama sudah running (lokal atau VPS/container).\n"
                f"Download: [/][{C_ACCENT}]https://ollama.com[/]\n\n"
                f"[{C_VAL}]Contoh URL[/]\n"
                f"  [{C_DIM}]•[/]  Lokal        [{C_ACCENT}]http://localhost:11434[/]\n"
                f"  [{C_DIM}]•[/]  VPS          [{C_ACCENT}]http://123.456.789.0:11434[/]\n"
                f"  [{C_DIM}]•[/]  Docker       [{C_ACCENT}]http://host.docker.internal:11434[/]\n"
                f"  [{C_DIM}]•[/]  Custom port  [{C_ACCENT}]http://123.456.789.0:10228[/]"
            ),
            padding=(0, 2),
        ))
        console.print()
        ollama_url = ask("Ollama URL", "http://localhost:11434") or "http://localhost:11434"
        model = ask("Model name", "llama3.2:latest") or "llama3.2:latest"
        config_lines += [
            f"OLLAMA_URL={ollama_url}",
            f"OLLAMA_MODEL={model}",
        ]

    # ── Simpan ke config path ─────────────────────────────────────────────────
    config_lines.append("DEFAULT_BRANCH=main")
    ENV_PATH.write_text("\n".join(config_lines) + "\n", encoding="utf-8")

    # ── Reload config ─────────────────────────────────────────────────────────
    _parse_env_file(ENV_PATH)
    global AI_PROVIDER, OPENAI_KEY, GROQ_KEY, OPENROUTER_KEY, OPENROUTER_MODEL, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, CLOUDFLARE_MODEL, OLLAMA_URL, OLLAMA_MODEL, OPENAI_MODEL, GROQ_MODEL
    AI_PROVIDER           = os.environ.get("AI_PROVIDER", "openrouter")
    OPENAI_KEY            = os.environ.get("OPENAI_API_KEY", "")
    GROQ_KEY              = os.environ.get("GROQ_API_KEY", "")
    OPENROUTER_KEY        = os.environ.get("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL      = os.environ.get("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
    CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    CLOUDFLARE_API_TOKEN  = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    CLOUDFLARE_MODEL      = os.environ.get("CLOUDFLARE_MODEL", "@cf/meta/llama-4-scout-17b-16e-instruct")
    OLLAMA_URL            = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL          = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
    OPENAI_MODEL          = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    GROQ_MODEL            = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

    console.print()
    console.print(card(
        Text.from_markup(
            f"[bold {C_OK}]✓  Setup selesai![/]\n\n"
            f"[{C_LABEL}]Konfigurasi disimpan di [/][{C_ACCENT}]{escape(str(_get_config_path()))}[/]\n"
            f"[{C_LABEL}]Untuk mengubah, edit file tersebut atau jalankan [/][{C_ACCENT}]autodeploy --setup[/]"
        ),
        "Ready", tone="ok",
    ))
    console.print()
    ui_wait("Tekan Enter untuk melanjutkan deploy...")

def run_uninstall():
    """Hapus konfigurasi dan uninstall package autodeploy-ai."""
    ui_clear()
    ui_banner()

    console.print(card(
        Text.from_markup(
            f"[bold {C_WARN}]Ini akan menghapus:[/]\n\n"
            f"  [{C_DIM}]•[/]  Config file  [{C_ACCENT}]{escape(str(_get_config_path()))}[/]\n"
            f"  [{C_DIM}]•[/]  Package      [{C_ACCENT}]autodeploy-ai[/]  [{C_DIM}](pip uninstall)[/]\n\n"
            f"[{C_LABEL}]Command [/][{C_ACCENT}]autodeploy[/][{C_LABEL}] tidak akan bisa dipakai lagi.[/]"
        ),
        "Uninstall", tone="warn",
    ))
    console.print()

    confirm = ask("Yakin? (y/N)").lower()

    if confirm not in ("y", "yes"):
        ui_cancel("Uninstall dibatalkan.")
        return
    # Hapus config file + folder (Windows: C:\ProgramData\autodeploy\)
    if ENV_PATH.exists():
        ENV_PATH.unlink()
        console.print(f"  [{C_OK}]✓[/]  Config dihapus  [{C_DIM}]{ENV_PATH}[/]")
    else:
        console.print(f"  [{C_DIM}]–[/]  Config tidak ditemukan, dilewati")

    # Hapus folder config kalau sudah kosong (khusus Windows ProgramData)
    config_dir = ENV_PATH.parent
    if config_dir != Path.home() and config_dir.exists():
        try:
            config_dir.rmdir()  # hanya berhasil kalau folder kosong
            console.print(f"  [{C_OK}]✓[/]  Folder dihapus  [{C_DIM}]{config_dir}[/]")
        except OSError:
            console.print(f"  [{C_DIM}]–[/]  Folder tidak kosong, dilewati")

    # Scripts dir dan site-packages
    scripts_dir = Path(sys.executable).parent / "Scripts" \
        if (Path(sys.executable).parent / "Scripts").exists() \
        else Path(sys.executable).parent

    # Buat script uninstall temporer untuk menghapus setelah kita keluar
    import tempfile
    import atexit
    import site
    import shutil

    uninstall_script = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8')
    uninstall_script.write(f'''
import sys
import subprocess
import time
import site
import shutil
from pathlib import Path

scripts_dir = Path(r"{scripts_dir}")
site_dirs = {site.getsitepackages()}

print("Menghapus sisa file autodeploy...")

# Tunggu sebentar agar proses utama selesai
time.sleep(1)

# Hapus semua autodeploy* di scripts
for f in scripts_dir.glob("autodeploy*"):
    try:
        f.unlink()
        print(f"  ✓ Hapus script: {{f.name}}")
    except Exception:
        pass

# Hapus package via pip
for pkg in ["autodeploy-ai", "autodeploy-cli", "autodeploy_ai", "autodeploy_cli"]:
    try:
        subprocess.run([sys.executable, "-m", "pip", "uninstall", pkg, "-y"],
                  capture_output=True, text=True)
        print(f"  ✓ Uninstall package: {{pkg}}")
    except Exception:
        pass

# Hapus sisa corrupt
for site_dir in site_dirs:
    site_path = Path(site_dir)
    if not site_path.exists():
        continue
    for entry in site_path.glob("~utodeploy*"):
        try:
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
            print(f"  ✓ Hapus sisa corrupt: {{entry.name}}")
        except Exception:
            pass

print()
print("✓ Uninstall selesai!")
''')
    uninstall_script.close()

    # Jalankan script uninstall di background tanpa buka jendela baru
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    subprocess.Popen([sys.executable, uninstall_script.name],
                startupinfo=startupinfo,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)

    console.print()
    console.print(card(
        Text.from_markup(
            f"[bold {C_OK}]Uninstall dimulai...[/]\n\n"
            f"[{C_LABEL}]Program akan keluar dan uninstall akan selesai dalam beberapa detik.[/]"
        ),
        "Uninstalling", tone="ok",
    ))
    console.print()

    # Keluar segera agar file exe kita tidak terkunci
    sys.exit(0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UI HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_TONES = {"line": C_LINE, "accent": C_ACCENT, "ok": C_OK, "warn": C_WARN, "err": C_ERR}
_TIMINGS: list[float] = []   # total waktu tiap step, untuk ringkasan akhir


def ui_clear():
    os.system("cls" if os.name == "nt" else "clear")


def _w() -> int:
    """Lebar konten maksimum — dibatasi supaya tetap rapi di terminal lebar."""
    return min(console.width, 100)


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def gradient_text(s: str, stops=BRAND_GRADIENT, bold: bool = True) -> Text:
    """Teks dengan gradient warna per-karakter (turun otomatis ke 256/16 warna)."""
    out = Text()
    segs = len(stops) - 1
    n = max(len(s) - 1, 1)
    for i, ch in enumerate(s):
        pos = i / n * segs
        k = min(int(pos), segs - 1)
        f = pos - k
        a, b = _hex_rgb(stops[k]), _hex_rgb(stops[k + 1])
        r, g, bl = (round(a[j] + (b[j] - a[j]) * f) for j in range(3))
        out.append(ch, style=f"{'bold ' if bold else ''}#{r:02x}{g:02x}{bl:02x}")
    return out


def badge(label: str, color: str, width: int = 5) -> Text:
    """Chip kecil berwarna, mis.  FREE  /  feat ."""
    t = Text(f" {label.center(width)} ")
    t.stylize(f"bold {C_INK} on {color}")   # stylize (bukan base style) → padding sel tidak ikut berwarna
    return t


def card(body, title: str = "", tone: str = "line", subtitle: str = "",
         padding: tuple[int, int] = (1, 2)) -> Panel:
    """Panel rounded dengan judul bertitik warna — pengganti Panel kotak lama."""
    color = _TONES.get(tone, C_LINE)
    dot = C_ACCENT if tone == "line" else color
    t = Text.assemble(("● ", dot), (title, f"bold {C_TEXT}")) if title else None
    sub = Text(subtitle, style=C_DIM) if subtitle else None
    return Panel(
        body, title=t, title_align="left", subtitle=sub, subtitle_align="right",
        border_style=color, box=box.ROUNDED, padding=padding, width=_w(),
    )


def hint(markup: str, tone: str = "line") -> Panel:
    """Kartu tipis tanpa judul untuk petunjuk singkat."""
    return card(Text.from_markup(markup), tone=tone, padding=(0, 2))


def kv(rows: list[tuple[str, object]], label_w: int = 9) -> Table:
    g = Table.grid(padding=(0, 2))
    g.add_column(style=C_LABEL, no_wrap=True, min_width=label_w)
    g.add_column(overflow="fold")
    for k, v in rows:
        g.add_row(k, v)
    return g


# ── Input ─────────────────────────────────────────────────────────────────────
def _pt(label: str) -> HTML:
    return HTML(f'<arrow>  ❯ </arrow><label>{_xml_escape(label)}  </label>')


def ask(label: str, placeholder: str = "") -> str:
    """Prompt satu baris. Ctrl+C / Ctrl+D dianggap pembatalan."""
    try:
        return pt_prompt(_pt(label), style=PT_STYLE, placeholder=placeholder or None).strip()
    except (KeyboardInterrupt, EOFError):
        raise KeyboardInterrupt


def ui_wait(message: str):
    try:
        console.print(f"  [{C_DIM}]{message}[/]", end="")
        input()
    except (KeyboardInterrupt, EOFError):
        pass


# ── Remote / commit helpers ───────────────────────────────────────────────────
def _remote_parts(remote: str) -> tuple[str, str]:
    """Return (teks tampilan, URL web). Credential di URL tidak ikut ditampilkan."""
    r = (remote or "").strip()
    if r.endswith(".git"):
        r = r[:-4]
    if r.startswith("git@github.com:"):
        path = r.split(":", 1)[1]
    elif "github.com/" in r:
        path = r.split("github.com/", 1)[1]
    else:
        return (remote or "not set"), ""
    path = path.strip("/")
    return f"github.com/{path}", f"https://github.com/{path}"


def remote_text(remote: str) -> Text:
    label, url = _remote_parts(remote)
    if not url:
        return Text(label, style=C_VAL)
    t = Text(label)
    t.stylize(Style(color=C_ACCENT, underline=True, link=url))
    return t


_COMMIT_RE = re.compile(r"^(\w+)(?:\(([^)]*)\))?(!)?:\s*(.+)$")
_TYPE_COLORS = {
    "feat": "#34d399", "fix": "#f87171", "docs": "#fbbf24", "style": "#5eead4",
    "refactor": "#fb923c", "chore": "#9ca3af", "test": "#a3e635",
}


def commit_text(msg: str) -> Text:
    """Render 'type(scope): deskripsi' dengan badge tipe berwarna."""
    msg = (msg or "").strip()
    m = _COMMIT_RE.match(msg)
    if not m:
        return Text(msg, style=f"bold {C_TEXT}")
    typ, scope, bang, desc = m.groups()
    t = Text()
    t.append_text(badge(typ.lower(), _TYPE_COLORS.get(typ.lower(), C_LABEL)))
    if scope:
        t.append(f"  {scope}", style=f"bold {C_ACCENT}")
    if bang:
        t.append("!", style=f"bold {C_ERR}")
    t.append(f"  {desc}", style=f"bold {C_TEXT}")
    return t


# ── Banner & session ──────────────────────────────────────────────────────────
def ui_banner():
    title = Text("  ")
    title.append("▲ ", style=f"bold {C_ACCENT}")
    title.append_text(gradient_text("autodeploy"))
    title.append("  ")
    title.append(f" v{APP_VERSION} ", style=f"{C_LABEL} on {C_CHIP}")
    console.print()
    console.print(title)
    console.print(Text("  git init  ·  ai commit  ·  auto push", style=C_DIM))
    console.print()


@contextmanager
def working(label: str):
    """Spinner transient (hilang setelah selesai) dengan indent konsisten."""
    spin = Spinner("dots", text=Text(f" {label}…", style=C_LABEL), style=C_ACCENT)
    with Live(Padding(spin, (0, 0, 0, 2)), console=console, transient=True,
              refresh_per_second=20):
        yield


def ui_splash():
    ui_clear()
    ui_banner()
    with working("Reading workspace"):
        time.sleep(0.35)


def _ai_model_label() -> str:
    if AI_PROVIDER == "openai":
        return OPENAI_MODEL
    if AI_PROVIDER == "groq":
        return GROQ_MODEL
    if AI_PROVIDER == "openrouter":
        return OPENROUTER_MODEL
    if AI_PROVIDER == "cloudflare":
        return CLOUDFLARE_MODEL.split("/")[-1]
    if AI_PROVIDER == "ollama":
        return OLLAMA_MODEL
    return "unknown"


def ui_header(repo_dir: str, branch: str, remote: str, ai_provider: str):
    ai = Text.assemble((ai_provider, f"bold {C_OK}"), ("  ·  ", C_LINE), (_ai_model_label(), C_DIM))
    body = kv([
        ("Project", Text(Path(repo_dir).name or repo_dir, style=f"bold {C_TEXT}")),
        ("Remote",  remote_text(remote)),
        ("Branch",  Text(branch or DEFAULT_BRANCH, style=C_ACCENT)),
        ("AI",      ai),
    ])
    console.print(card(body, "Session", padding=(1, 2)))


def ui_tips():
    t = Text("  ")
    for key, desc in (("↵", "terima pesan AI"), ("ketik", "untuk override"), ("ctrl+c", "batal")):
        t.append(f" {key} ", style=f"{C_VAL} on {C_CHIP}")
        t.append(f" {desc}    ", style=C_DIM)
    console.print(t)
    console.print()


# ── Status lines ──────────────────────────────────────────────────────────────
def ui_done(label: str, ok: bool = True, elapsed: float | None = None, detail: str = ""):
    """Baris hasil satu step:  ✓  Staging changes      0.1s"""
    if elapsed is not None:
        _TIMINGS.append(elapsed)
    t = Text("  ")
    t.append("✓" if ok else "✗", style=f"bold {C_OK if ok else C_ERR}")
    t.append("  ")
    t.append(label.ljust(26), style=C_TEXT if ok else C_ERR)
    if elapsed is not None:
        t.append(f"{elapsed:>5.1f}s", style=C_DIM)
    if detail:
        t.append(f"   {detail}", style=C_DIM)
    console.print(t)


def ui_step(label: str, value: str = ""):
    t = Text("  ")
    t.append("›", style=f"bold {C_ACCENT}")
    t.append(f"  {label}", style=C_TEXT)
    if value:
        t.append(f"  {value}", style=C_DIM)
    console.print(t)


def ui_warn(message: str):
    console.print()
    console.print(Text.assemble("  ", ("▲", f"bold {C_WARN}"), "  ", (message, C_WARN)))
    console.print()


def ui_cancel(message: str):
    console.print()
    console.print(Text.assemble("  ", ("●", C_WARN), "  ", (message, C_DIM)))
    console.print()


def ui_error(message: str, hints: list[str] | None = None,
             hint_label: str = "Kemungkinan penyebab", detail: str = ""):
    parts: list = [Text(str(message), style=f"bold {C_TEXT}")]
    if hints:
        parts.append(Text(""))
        parts.append(Text(hint_label, style=C_LABEL))
        for h in hints:
            parts.append(Text.assemble(("  •  ", C_DIM), (h, C_VAL)))
    if detail:
        parts.append(Text(""))
        parts.append(Text(detail, style=C_DIM))
    console.print()
    console.print(card(Group(*parts), "Error", tone="err"))
    console.print()


def ui_success(commit_msg: str, branch: str, remote: str, sha: str = "", elapsed: float | None = None):
    commit = commit_text(commit_msg)
    if sha:
        commit.append(f"   {sha}", style=C_DIM)
    body = kv([
        ("Commit", commit),
        ("Branch", Text(branch, style=C_ACCENT)),
        ("Remote", remote_text(remote)),
    ])
    sub = f"selesai dalam {elapsed:.1f}s" if elapsed else ""
    console.print()
    console.print(card(body, "Deploy complete", tone="ok", subtitle=sub))
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GIT HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def spin_run(cmd: list[str], label: str, detail: str = "",
             interactive: bool = False) -> subprocess.CompletedProcess:
    """
    Jalankan command dengan spinner, lalu cetak baris hasil (✓/✗ + durasi).
    interactive=True → tanpa spinner & tanpa capture, supaya prompt login Git
    tidak tertimpa animasi.
    """
    t0 = time.perf_counter()
    if interactive:
        ui_step(f"{label}…")
        result = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace")
    else:
        with working(label):
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
            )
    ui_done(label, ok=result.returncode == 0, elapsed=time.perf_counter() - t0, detail=detail)
    return result


def git_has_changes() -> bool:
    return bool((run(["git", "status", "--porcelain"], capture=True).stdout or "").strip())


def git_has_unpushed_commits() -> bool:
    """Return True kalau ada commit lokal yang belum di-push ke remote."""
    result = run(["git", "log", "@{u}..", "--oneline"], capture=True)
    # Kalau tidak ada upstream (repo baru), anggap ada yang perlu di-push
    if result.returncode != 0:
        return True
    return bool((result.stdout or "").strip())


def git_current_branch() -> str:
    # symbolic-ref tetap bekerja di repo baru yang belum punya commit
    # (rev-parse --abbrev-ref mengembalikan "HEAD" di kondisi itu)
    result = run(["git", "symbolic-ref", "--short", "-q", "HEAD"], capture=True)
    name = (result.stdout or "").strip()
    if not name:
        result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True)
        name = (result.stdout or "").strip()
    return name or DEFAULT_BRANCH


def git_remote_url() -> str:
    result = run(["git", "remote", "get-url", "origin"], capture=True)
    return (result.stdout or "").strip()


def git_diff_staged() -> str:
    stat = (run(["git", "diff", "--staged", "--stat"], capture=True).stdout or "").strip()
    diff = (run(["git", "diff", "--staged", "--unified=3"], capture=True).stdout or "").strip()
    # Ollama (lokal/VPS) pakai limit lebih kecil supaya tidak timeout
    MAX = 1500 if AI_PROVIDER == "ollama" else 3500
    if len(diff) > MAX:
        diff = diff[:MAX] + "\n...(truncated)"
    return f"{stat}\n\n{diff}".strip()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AI COMMIT MESSAGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_prompt(diff: str) -> str:
    return (
        "You are a Git commit message generator. "
        "Based on the following staged diff, write ONE concise commit message in English.\n"
        "Format: <type>(<scope>): <short description>\n"
        "Types: feat, fix, docs, style, refactor, chore, test\n"
        "Rules: single line only, no extra explanation, max 72 characters.\n\n"
        f"DIFF:\n{diff}"
    )


def _call_openai(diff: str) -> str:
    import urllib.request
    payload = json.dumps({
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": _build_prompt(diff)}],
        "max_tokens": 100,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip().strip('"')


def _call_groq(diff: str) -> str:
    import urllib.request
    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": _build_prompt(diff)}],
        "max_tokens": 100,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_KEY}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip().strip('"')


def _call_openrouter(diff: str) -> str:
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": _build_prompt(diff)}],
        "max_tokens": 100,
        "temperature": 0.3,
    }).encode()

    for attempt in range(3):
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "HTTP-Referer": "https://github.com/autodeploy-ai",
                "X-Title": "AutoDeploy CLI",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"].strip().strip('"')
            # Strip thinking tags jika ada (beberapa model reasoning)
            if "<think>" in content:
                content = content.split("</think>")[-1].strip().strip('"')
            return content
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise


def _call_cloudflare(diff: str) -> str:
    import urllib.request
    payload = json.dumps({
        "messages": [{"role": "user", "content": _build_prompt(diff)}],
        "max_tokens": 100,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_MODEL}",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["result"]["response"].strip().strip('"').strip("`")


def _call_ollama(diff: str) -> str:
    import urllib.request
    import threading

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": _build_prompt(diff),
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    result_box: list = []
    error_box:  list = []

    def _do_request():
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result_box.append(json.loads(resp.read()))
        except Exception as e:
            error_box.append(e)

    t = threading.Thread(target=_do_request, daemon=True)
    t.start()

    # Tunggu sambil tetap bisa di-interrupt Ctrl+C
    while t.is_alive():
        t.join(timeout=0.2)

    if error_box:
        raise error_box[0]
    if not result_box:
        raise RuntimeError("Ollama tidak merespons")

    return result_box[0].get("response", "").strip().strip('"')


def generate_commit_message(diff: str) -> str:
    """Generate AI commit message pakai spinner, lalu user confirm atau override."""
    ai_msg = ""
    t0 = time.perf_counter()

    try:
        with working("Generating commit message"):
            if AI_PROVIDER == "openai":
                if not OPENAI_KEY:
                    raise ValueError("OPENAI_API_KEY tidak ada di .env")
                ai_msg = _call_openai(diff)
            elif AI_PROVIDER == "groq":
                if not GROQ_KEY:
                    raise ValueError("GROQ_API_KEY tidak ada di .env")
                ai_msg = _call_groq(diff)
            elif AI_PROVIDER == "openrouter":
                if not OPENROUTER_KEY:
                    raise ValueError("OPENROUTER_API_KEY tidak ada di .env")
                ai_msg = _call_openrouter(diff)
            elif AI_PROVIDER == "cloudflare":
                if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
                    raise ValueError("CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN tidak ada di .env")
                ai_msg = _call_cloudflare(diff)
            elif AI_PROVIDER == "ollama":
                ai_msg = _call_ollama(diff)
            else:
                raise ValueError(f"AI provider tidak dikenal: {AI_PROVIDER}")
    except Exception as exc:
        ai_msg = ""
        ui_done("Generating commit message", ok=False, elapsed=time.perf_counter() - t0)
        ui_warn(f"AI gagal: {str(exc)}")
    else:
        if ai_msg:
            ui_done("Generating commit message", elapsed=time.perf_counter() - t0)

    if ai_msg:
        console.print()
        console.print(card(
            commit_text(ai_msg), "Suggested commit",
            subtitle="",
            padding=(1, 2),
        ))
        console.print()
        try:
            override = pt_prompt(
                _pt("commit"),
                style=PT_STYLE,
                placeholder="tekan Enter untuk terima, atau ketik pesan sendiri",
            ).strip()
        except EOFError:
            return ai_msg
        except KeyboardInterrupt:
            raise
        return override if override else ai_msg

    # AI failed — manual fallback
    ui_warn("AI tidak bisa generate commit message. Masukkan manual:")
    try:
        msg = pt_prompt(
            _pt("commit"),
            style=PT_STYLE,
            placeholder="mis. feat(auth): add login endpoint",
        ).strip()
    except EOFError:
        msg = ""
    except KeyboardInterrupt:
        raise
    return msg


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GITHUB CREDENTIAL HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def is_auth_error(stderr: str) -> bool:
    """Deteksi apakah git push gagal karena masalah autentikasi."""
    if not stderr:
        return False
    stderr_lower = stderr.lower()
    auth_signals = [
        "authentication failed",
        "authorization failed",
        "invalid username or password",
        "remote: support for password authentication was removed",
        "403",
        "401",
        "could not read username",
        "could not read password",
        "permission denied",
        "fatal: repository not found",  # sering muncul saat akun salah
        "remote: repository not found",
    ]
    return any(s in stderr_lower for s in auth_signals)


def clear_github_credentials() -> bool:
    """
    Hapus credential GitHub dari:
    1. Windows Credential Manager (cmdkey) — target: git:https://github.com
    2. Git Credential Manager cache (git credential reject)
    Return True kalau berhasil hapus setidaknya satu.
    """
    cleared = False

    # ── 1. Windows Credential Manager via cmdkey ──────────────────────────────
    if sys.platform == "win32":
        targets = [
            "git:https://github.com",
            "git:https://www.github.com",
            "github.com",
        ]
        for target in targets:
            try:
                result = subprocess.run(
                    ["cmdkey", f"/delete:{target}"],
                    capture_output=True, text=True,
                )
                if result.returncode == 0:
                    cleared = True
            except Exception:
                pass

    # ── 2. Git credential reject (cross-platform, hapus dari cache/store) ─────
    credential_input = "protocol=https\nhost=github.com\n\n"
    try:
        subprocess.run(
            ["git", "credential", "reject"],
            input=credential_input,
            capture_output=True,
            text=True,
        )
        cleared = True
    except Exception:
        pass

    return cleared


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  VALIDATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def validate_github_url(url: str) -> tuple[bool, str]:
    """Cek apakah repo GitHub benar-benar ada. Return (valid, pesan_error)."""
    import urllib.request
    import urllib.error

    # Normalisasi URL — ambil bagian username/repo saja
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    # Ekstrak path dari URL
    # Support: https://github.com/user/repo atau git@github.com:user/repo
    if url.startswith("git@github.com:"):
        path = url.replace("git@github.com:", "")
    elif "github.com/" in url:
        path = url.split("github.com/")[-1]
    else:
        return False, "URL bukan GitHub. Gunakan format https://github.com/username/repo"

    parts = path.strip("/").split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return False, "Format URL tidak valid. Contoh: https://github.com/username/repo"

    api_url = f"https://api.github.com/repos/{parts[0]}/{parts[1]}"
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "AutoDeploy-CLI/1.7"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return True, ""
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, f"Repo tidak ditemukan: [bold]{parts[0]}/{parts[1]}[/bold]\nBuat repo baru di [{C_ACCENT}]https://github.com/new[/] terlebih dahulu."
        elif e.code == 403:
            # Rate limited tapi repo kemungkinan ada
            return True, ""
        return False, f"GitHub mengembalikan error {e.code}."
    except Exception:
        # Tidak bisa cek (offline, timeout) — lanjut saja
        return True, ""

    return False, "Tidak bisa memvalidasi URL."


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN DEPLOY FLOW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _new_repo_body() -> Group:
    steps = kv([
        ("1", Text.from_markup(f"[{C_VAL}]Buka [/][underline {C_ACCENT}]https://github.com/new[/][{C_VAL}] dan buat repo kosong[/]")),
        ("2", Text("Copy URL repo-nya", style=C_VAL)),
        ("3", Text("Paste di bawah ↓", style=C_VAL)),
    ], label_w=1)
    return Group(
        Text.from_markup(f"[{C_LABEL}]Project ini belum punya [/][{C_ACCENT}].git[/][{C_LABEL}] — akan di-init otomatis.[/]"),
        Text(""),
        Text.from_markup(f"[bold {C_WARN}]▲[/] [{C_WARN}]Pastikan repo baru sudah dibuat di GitHub lebih dulu.[/]"),
        Text(""),
        steps,
    )


def deploy(github_url: str = ""):
    ui_splash()

    cwd          = os.getcwd()
    is_git_repo  = Path(".git").is_dir()
    remote       = ""
    branch       = DEFAULT_BRANCH

    # ── Inisialisasi repo baru ────────────────────────────────────────────────
    if not is_git_repo:
        while True:
            if not github_url:
                ui_clear()
                ui_banner()
                console.print(card(_new_repo_body(), "New repository"))
                console.print()
                github_url = ask("github url", "https://github.com/username/repo")

                if not github_url:
                    ui_warn("URL tidak boleh kosong.")
                    time.sleep(1)
                    continue

            # Validasi repo
            t0 = time.perf_counter()
            with working("Checking repository"):
                valid, err_msg = validate_github_url(github_url)

            if valid:
                ui_done("Repository found", elapsed=time.perf_counter() - t0)
                break
            else:
                # Tampil error, tunggu Enter, lalu ulang dari awal
                console.print()
                console.print(card(
                    Text.from_markup(
                        f"[bold {C_ERR}]✗  Repository tidak valid[/]\n\n"
                        f"[{C_TEXT}]{err_msg}[/]"
                    ),
                    "Repository check", tone="err",
                ))
                console.print()
                try:
                    console.print(f"  [{C_DIM}]Tekan Enter untuk coba lagi...[/]", end="")
                    input()
                except (KeyboardInterrupt, EOFError):
                    raise KeyboardInterrupt
                github_url = ""  # reset, ulang dari awal

        if not github_url:
            ui_error("GitHub URL diperlukan untuk repo baru.")
            sys.exit(1)

        ui_step("git init")
        run(["git", "init"])
        run(["git", "checkout", "-b", DEFAULT_BRANCH])

        ui_step("git remote add origin", _remote_parts(github_url)[0])
        run(["git", "remote", "add", "origin", github_url])
        remote = github_url

    else:
        remote = git_remote_url()
        branch = git_current_branch()

        # Repo ada tapi remote belum di-set
        if not remote:
            if not github_url:
                console.print()
                console.print(card(
                    Text("Repo ditemukan tapi belum punya remote origin. Masukkan GitHub URL.", style=C_LABEL),
                    "Set remote",
                ))
                console.print()
                github_url = ask("github url", "https://github.com/username/repo")

            if not github_url:
                ui_error("GitHub URL diperlukan.")
                sys.exit(1)

            ui_step("git remote add origin", _remote_parts(github_url)[0])
            run(["git", "remote", "add", "origin", github_url])
            remote = github_url

    branch = git_current_branch()

    # ── Tampilkan header ──────────────────────────────────────────────────────
    ui_clear()
    ui_banner()
    ui_header(cwd, branch, remote, AI_PROVIDER)
    console.print()
    ui_tips()
    _TIMINGS.clear()

    # ── Cek perubahan ─────────────────────────────────────────────────────────
    has_changes  = git_has_changes()
    has_unpushed = git_has_unpushed_commits()

    if not has_changes and not has_unpushed:
        console.print(card(
            Text("Semua file sudah up to date. Tidak ada yang perlu di-commit.", style=C_LABEL),
            "No changes", tone="warn",
        ))
        console.print()
        ui_wait("Press Enter to exit...")
        sys.exit(0)

    # ── Kalau ada unpushed commits tapi working tree bersih — langsung push ──
    if not has_changes and has_unpushed:
        sha = (run(["git", "rev-parse", "--short", "HEAD"], capture=True).stdout or "").strip()
        commit_msg = (run(["git", "log", "-1", "--pretty=%s"], capture=True).stdout or "").strip()
        result = spin_run(["git", "push", "-u", "origin", branch], "Pushing to GitHub",
                          detail=f"origin/{branch}")
        if result.returncode != 0:
            stderr_txt = (result.stderr or "").strip()
            if is_auth_error(stderr_txt):
                console.print()
                console.print(card(
                    Text.from_markup(
                        f"[bold {C_WARN}]Autentikasi GitHub gagal.[/]\n\n"
                        f"[{C_LABEL}]Credential lama akan dihapus agar kamu bisa login ulang.[/]"
                    ),
                    "Auth error", tone="warn",
                ))
                console.print()
                ui_step("Clearing GitHub credentials")
                cleared = clear_github_credentials()
                console.print(f"  [{C_OK}]✓[/]  Credential dihapus" if cleared else f"  [{C_WARN}]▲[/]  Tidak ada credential yang dihapus")
                console.print()
                result = spin_run(["git", "push", "-u", "origin", branch], "Retrying push",
                                  detail=f"origin/{branch}", interactive=True)
                ui_clear()
                ui_banner()
                if result.returncode != 0:
                    ui_error("git push tetap gagal.", detail=(result.stderr or "").strip())
                    sys.exit(1)
            else:
                ui_error("git push gagal.", detail=stderr_txt)
                sys.exit(1)
        ui_success(commit_msg, branch, remote, sha=sha, elapsed=sum(_TIMINGS))
        sys.exit(0)

    # ── git add . ─────────────────────────────────────────────────────────────
    result = spin_run(["git", "add", "."], "Staging changes")

    # ── Ambil diff ────────────────────────────────────────────────────────────
    diff = git_diff_staged()

    # ── AI commit message ─────────────────────────────────────────────────────
    commit_msg = generate_commit_message(diff)
    if not commit_msg:
        ui_error("Commit message kosong. Deploy dibatalkan.")
        sys.exit(1)
    console.print()

    # ── git commit ────────────────────────────────────────────────────────────
    result = spin_run(["git", "commit", "-m", commit_msg], "Creating commit")
    if result.returncode != 0:
        ui_error("git commit gagal.", detail=(result.stderr or "").strip())
        sys.exit(1)
    sha = (run(["git", "rev-parse", "--short", "HEAD"], capture=True).stdout or "").strip()

    # ── git push ──────────────────────────────────────────────────────────────
    result = spin_run(["git", "push", "-u", "origin", branch], "Pushing to GitHub",
                      detail=f"origin/{branch}")
    if result.returncode != 0:
        stderr_txt = (result.stderr or "").strip()

        # ── Cek apakah error karena autentikasi ───────────────────────────────
        if is_auth_error(stderr_txt):
            console.print()
            console.print(card(
                Text.from_markup(
                    f"[bold {C_WARN}]Autentikasi GitHub gagal.[/]\n\n"
                    f"[{C_LABEL}]Kemungkinan kamu sedang login dengan akun GitHub yang berbeda.\n"
                    f"Credential lama akan dihapus agar kamu bisa login ulang.[/]"
                ),
                "Auth error", tone="warn",
            ))
            console.print()

            # Hapus credential GitHub
            ui_step("Clearing GitHub credentials")
            cleared = clear_github_credentials()
            if cleared:
                console.print(f"  [{C_OK}]✓[/]  Credential dihapus")
            else:
                console.print(f"  [{C_WARN}]▲[/]  Tidak ada credential yang dihapus (mungkin sudah kosong)")

            console.print()
            console.print(card(
                Text.from_markup(
                    f"[bold {C_TEXT}]Silakan login dengan akun GitHub yang benar.[/]\n\n"
                    f"[{C_LABEL}]Git akan meminta username & password/token saat push berikutnya.\n"
                    f"Gunakan [/][{C_ACCENT}]Personal Access Token[/][{C_LABEL}] sebagai password.\n"
                    f"Buat token di: [/][underline {C_ACCENT}]https://github.com/settings/tokens[/]"
                ),
                "Login ulang",
            ))
            console.print()

            # Retry push sekali — Git akan trigger login prompt
            # (interactive: tanpa spinner supaya prompt login tidak tertimpa)
            result = spin_run(["git", "push", "-u", "origin", branch], "Retrying push",
                              detail=f"origin/{branch}", interactive=True)
            ui_clear()
            ui_banner()
            if result.returncode != 0:
                ui_error(
                    "git push tetap gagal setelah login ulang.",
                    hints=["Token memiliki scope repo", "Kamu punya akses write ke repo ini"],
                    hint_label="Pastikan",
                    detail=(result.stderr or "").strip(),
                )
                sys.exit(1)
        else:
            # Error bukan karena auth
            ui_error(
                "git push gagal.",
                hints=["Remote URL salah", "Belum ada akses ke repo", "Branch belum ada di remote"],
                detail=stderr_txt,
            )
            sys.exit(1)

    ui_success(commit_msg, branch, remote, sha=sha, elapsed=sum(_TIMINGS))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HISTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_history(n: int = 10):
    """Tampilkan n commit terakhir dengan UI rapi."""
    ui_clear()
    ui_banner()

    if not Path(".git").is_dir():
        ui_error("Folder ini bukan git repo.", hints=["Jalankan autodeploy terlebih dahulu untuk init repo"])
        sys.exit(1)

    result = run(
        ["git", "log", f"-{n}", "--pretty=format:%h|%ar|%s|%an"],
        capture=True,
    )
    raw = (result.stdout or "").strip()

    if not raw:
        console.print(card(
            Text("Belum ada commit di repo ini.", style=C_LABEL),
            "History", tone="warn",
        ))
        console.print()
        return

    t = Table.grid(padding=(0, 2))
    t.add_column(style=C_DIM,    no_wrap=True)   # sha
    t.add_column(style=C_LABEL,  no_wrap=True)   # waktu
    t.add_column(overflow="fold")                # pesan
    t.add_column(style=C_DIM,    no_wrap=True)   # author

    for line in raw.splitlines():
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        sha, when, msg, author = parts
        t.add_row(
            sha,
            when,
            commit_text(msg),
            author,
        )

    branch  = git_current_branch()
    remote  = git_remote_url()
    sub     = f"{branch}  ·  {_remote_parts(remote)[0]}" if remote else branch

    console.print(card(t, f"Last {n} commits", subtitle=sub))
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SWITCH PROVIDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_switch_provider():
    """Ganti AI provider tanpa setup ulang dari awal."""
    ui_clear()
    ui_banner()

    # Baca config lama supaya key yang sudah ada tidak hilang
    old_lines: list[str] = []
    if ENV_PATH.exists():
        old_lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    def _get_old(key: str) -> str:
        for l in old_lines:
            if l.startswith(f"{key}="):
                return l.split("=", 1)[1].strip()
        return ""

    current = os.environ.get("AI_PROVIDER", "")
    console.print(card(
        Text.from_markup(
            f"[{C_LABEL}]Provider aktif sekarang: [/][bold {C_ACCENT}]{current or '(belum di-set)'}[/]"
        ),
        "Switch AI Provider",
    ))
    console.print()
    console.print(card(_provider_table(), "Pilih provider baru"))
    console.print()

    while True:
        choice = ask("Provider (1/2/3/4/5)")
        if choice in {"1", "2", "3", "4", "5"}:
            provider = PROVIDERS[int(choice) - 1][0]
            break
        ui_warn("Masukkan 1, 2, 3, 4, atau 5.")

    # Pertahankan semua key lama, hanya timpa yang relevan
    keep = {l.split("=", 1)[0]: l.split("=", 1)[1] for l in old_lines if "=" in l}
    keep["AI_PROVIDER"] = provider

    if provider == "openrouter":
        old_key = _get_old("OPENROUTER_API_KEY")
        console.print()
        if old_key:
            console.print(hint(f"[{C_LABEL}]API key sebelumnya: [/][{C_DIM}]{old_key[:8]}…[/]  [{C_LABEL}](tekan Enter untuk pakai)[/]"))
            console.print()
        while True:
            key = ask("OpenRouter API Key", old_key or "sk-or-...")
            key = key or old_key
            if key.startswith("sk-or-") and len(key) > 20:
                break
            ui_warn("API key tidak valid. Harus diawali 'sk-or-'.")
        keep["OPENROUTER_API_KEY"] = key
        keep.setdefault("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")

    elif provider == "cloudflare":
        old_id    = _get_old("CLOUDFLARE_ACCOUNT_ID")
        old_token = _get_old("CLOUDFLARE_API_TOKEN")
        console.print()
        while True:
            account_id = ask("Account ID", old_id or "01b402d8ebd6d105b6dd06a792a704b7")
            account_id = account_id or old_id
            if len(account_id) >= 32:
                break
            ui_warn("Account ID tidak valid.")
        while True:
            cf_token = ask("API Token", old_token or "cfut_...")
            cf_token = cf_token or old_token
            if len(cf_token) > 20:
                break
            ui_warn("API Token tidak valid.")
        cf_model = ask("Model", _get_old("CLOUDFLARE_MODEL") or "@cf/meta/llama-4-scout-17b-16e-instruct")
        keep["CLOUDFLARE_ACCOUNT_ID"] = account_id
        keep["CLOUDFLARE_API_TOKEN"]  = cf_token
        keep["CLOUDFLARE_MODEL"]      = cf_model or "@cf/meta/llama-4-scout-17b-16e-instruct"

    elif provider == "groq":
        old_key = _get_old("GROQ_API_KEY")
        console.print()
        if old_key:
            console.print(hint(f"[{C_LABEL}]API key sebelumnya: [/][{C_DIM}]{old_key[:8]}…[/]  [{C_LABEL}](tekan Enter untuk pakai)[/]"))
            console.print()
        while True:
            key = ask("Groq API Key", old_key or "gsk_...")
            key = key or old_key
            if key.startswith("gsk_") and len(key) > 20:
                break
            ui_warn("API key tidak valid. Harus diawali 'gsk_'.")
        keep["GROQ_API_KEY"] = key
        keep.setdefault("GROQ_MODEL", "llama-3.1-8b-instant")

    elif provider == "openai":
        old_key = _get_old("OPENAI_API_KEY")
        console.print()
        if old_key:
            console.print(hint(f"[{C_LABEL}]API key sebelumnya: [/][{C_DIM}]{old_key[:8]}…[/]  [{C_LABEL}](tekan Enter untuk pakai)[/]"))
            console.print()
        while True:
            key = ask("OpenAI API Key", old_key or "sk-...")
            key = key or old_key
            if key.startswith("sk-") and len(key) > 20:
                break
            ui_warn("API key tidak valid. Harus diawali 'sk-'.")
        keep["OPENAI_API_KEY"] = key
        keep.setdefault("OPENAI_MODEL", "gpt-4o-mini")

    elif provider == "ollama":
        old_url   = _get_old("OLLAMA_URL")
        old_model = _get_old("OLLAMA_MODEL")
        console.print()
        ollama_url = ask("Ollama URL", old_url or "http://localhost:11434")
        model      = ask("Model name", old_model or "llama3.2:latest")
        keep["OLLAMA_URL"]   = ollama_url or old_url or "http://localhost:11434"
        keep["OLLAMA_MODEL"] = model or old_model or "llama3.2:latest"

    keep.setdefault("DEFAULT_BRANCH", "main")

    # Tulis ulang config
    ENV_PATH.write_text(
        "\n".join(f"{k}={v}" for k, v in keep.items()) + "\n",
        encoding="utf-8",
    )
    _parse_env_file(ENV_PATH)

    console.print()
    console.print(card(
        Text.from_markup(
            f"[bold {C_OK}]✓  Provider berhasil diganti![/]\n\n"
            f"[{C_LABEL}]Aktif sekarang: [/][bold {C_ACCENT}]{provider}[/]"
        ),
        "Done", tone="ok",
    ))
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UPDATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _fetch_latest_version() -> str:
    """Ambil versi terbaru autodeploy-ai dari PyPI. Return string versi atau ''."""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(
            "https://pypi.org/pypi/autodeploy-ai/json",
            headers={"User-Agent": "AutoDeploy-CLI"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data["info"]["version"]
    except Exception:
        return ""


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:
        return (0,)


def run_update():
    """Periksa versi terbaru di PyPI, tawarkan update jika ada."""
    ui_clear()
    ui_banner()

    t0 = time.perf_counter()
    with working("Memeriksa versi terbaru"):
        latest = _fetch_latest_version()

    if not latest:
        ui_done("Periksa versi", ok=False, elapsed=time.perf_counter() - t0)
        ui_error(
            "Tidak bisa terhubung ke PyPI.",
            hints=["Periksa koneksi internet", "Coba lagi beberapa saat"],
        )
        sys.exit(1)

    ui_done("Periksa versi", elapsed=time.perf_counter() - t0)
    console.print()

    current = APP_VERSION
    is_outdated = _version_tuple(latest) > _version_tuple(current)

    if not is_outdated:
        console.print(card(
            kv([
                ("Terpasang", Text(current, style=f"bold {C_OK}")),
                ("Terbaru",   Text(latest,  style=C_DIM)),
            ]),
            "Sudah versi terbaru ✓", tone="ok",
        ))
        console.print()
        return

    console.print(card(
        kv([
            ("Terpasang", Text(current, style=f"bold {C_WARN}")),
            ("Terbaru",   Text(latest,  style=f"bold {C_OK}")),
        ]),
        "Update tersedia", tone="warn",
    ))
    console.print()

    confirm = ask(f"Install v{latest} sekarang? (Y/n)").lower()
    if confirm in ("n", "no"):
        ui_cancel("Update dibatalkan.")
        return

    console.print()
    t0 = time.perf_counter()
    with working(f"Menginstall autodeploy-ai v{latest}"):
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "autodeploy-ai", "-q"],
            capture_output=True, text=True,
        )
    ui_done(f"Install v{latest}", ok=result.returncode == 0, elapsed=time.perf_counter() - t0)

    if result.returncode != 0:
        ui_error("Install gagal.", detail=(result.stderr or "").strip())
        sys.exit(1)

    console.print()
    console.print(card(
        Text.from_markup(
            f"[bold {C_OK}]✓  Update selesai![/]\n\n"
            f"[{C_LABEL}]autodeploy-ai [/][bold {C_TEXT}]v{current}[/]"
            f"[{C_LABEL}]  →  [/][bold {C_OK}]v{latest}[/]"
        ),
        "Done", tone="ok",
    ))
    console.print()




def run_help():
    ui_clear()
    ui_banner()

    commands = [
        ("autodeploy",                   "Deploy perubahan ke GitHub — staging, AI commit, push otomatis"),
        ("autodeploy <url>",             "Deploy sekaligus set remote URL (untuk repo baru)"),
        ("autodeploy --history",         "Tampilkan 10 commit terakhir"),
        ("autodeploy --history <n>",     "Tampilkan n commit terakhir"),
        ("autodeploy --switch-provider", "Ganti AI provider tanpa setup ulang"),
        ("autodeploy --update",          "Periksa dan install versi terbaru"),
        ("autodeploy --setup",           "Jalankan setup wizard dari awal"),
        ("autodeploy --uninstall",       "Hapus konfigurasi dan uninstall package"),
        ("autodeploy -h",                "Tampilkan halaman bantuan ini"),
    ]

    t = Table.grid(padding=(0, 3))
    t.add_column(style=f"bold {C_ACCENT}", no_wrap=True)
    t.add_column(style=C_LABEL, overflow="fold")

    for cmd, desc in commands:
        t.add_row(cmd, desc)

    console.print(card(t, "Commands", padding=(1, 2)))

    # Info provider aktif
    provider = os.environ.get("AI_PROVIDER", "(belum di-set)")
    model    = _ai_model_label()
    console.print()
    console.print(card(
        kv([
            ("Provider", Text(provider, style=f"bold {C_OK}")),
            ("Model",    Text(model,    style=C_DIM)),
            ("Config",   Text(str(ENV_PATH), style=C_DIM)),
        ]),
        "Active config",
    ))
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRYPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main_cli():
    """Entrypoint untuk global CLI command `autodeploy`."""
    args = sys.argv[1:]

    if "-h" in args or "--help" in args:
        run_help()
        sys.exit(0)

    if "--history" in args:
        idx = args.index("--history")
        n = 10
        if idx + 1 < len(args) and args[idx + 1].isdigit():
            n = int(args[idx + 1])
        run_history(n)
        sys.exit(0)

    if "--switch-provider" in args:
        try:
            run_switch_provider()
        except KeyboardInterrupt:
            ui_cancel("Switch provider dibatalkan")
        sys.exit(0)

    if "--update" in args or "--upgrade" in args:
        try:
            run_update()
        except KeyboardInterrupt:
            ui_cancel("Update dibatalkan")
        sys.exit(0)

    # Flag --setup → paksa jalankan wizard ulang
    if "--setup" in args:
        try:
            run_setup_wizard()
        except KeyboardInterrupt:
            ui_cancel("Setup dibatalkan")
        sys.exit(0)

    # Flag --uninstall → hapus config dan uninstall package
    if "--uninstall" in args:
        try:
            run_uninstall()
        except KeyboardInterrupt:
            ui_cancel("Uninstall dibatalkan")
        sys.exit(0)

    # Pertama kali — belum dikonfigurasi
    if not is_configured():
        try:
            run_setup_wizard()
        except KeyboardInterrupt:
            ui_cancel("Setup dibatalkan")
            sys.exit(0)

    github_url = args[0] if args and not args[0].startswith("--") else ""
    try:
        deploy(github_url)
    except KeyboardInterrupt:
        ui_cancel("Deploy dibatalkan")
        sys.exit(0)


if __name__ == "__main__":
    main_cli()