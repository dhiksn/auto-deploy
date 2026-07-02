#!/usr/bin/env python3
"""
┌────────────────────────────────────────────────┐
│              AutoDeploy CLI                    │
│     Git Init · AI Commit · Auto Push           │
│                                                │
│  Requires:                                     │
│    pip install rich prompt_toolkit             │
└────────────────────────────────────────────────┘

"""

# ── Standard library ──────────────────────────────────────────────────────────
import os
import sys
import json
import subprocess
import time
import threading
from pathlib import Path

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

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.box import DOUBLE_EDGE, SQUARE, MINIMAL
from rich.progress import Progress, BarColumn, TextColumn
from rich.markup import escape
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.formatted_text import HTML

# ── Console ───────────────────────────────────────────────────────────────────
console = Console(highlight=False, soft_wrap=True)

APP_VERSION = "1.5.6"

# ── Theme: teal + amber (no purple, no blue) ──────────────────────────────────
C_HEAD   = "bold turquoise2"
C_LINE   = "grey42"
C_LABEL  = "grey62"
C_VAL    = "wheat1"
C_OK     = "sea_green2"
C_WARN   = "dark_orange"
C_ERR    = "bright_red"
C_DIM    = "grey35"
C_TEXT   = "white"
C_ACCENT = "turquoise2"
C_DIM_ANSI = "2"   # ANSI dim untuk sys.stdout.write

PT_STYLE = PTStyle.from_dict({
    "prompt":      "bold ansigreen",
    "placeholder": "ansibrightblack",
    "": "ansiwhite",
})

LOGO = "Slant"  # pyfiglet font

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


def load_env():
    # 1. Home directory config (~/.autodeploy.env) — berlaku global
    _parse_env_file(Path.home() / ".autodeploy.env")
    # 2. Local project .env — override home config
    _parse_env_file(Path(__file__).parent / ".env")


load_env()

# ── Config ────────────────────────────────────────────────────────────────────
AI_PROVIDER    = os.environ.get("AI_PROVIDER", "openai")
OPENAI_KEY     = os.environ.get("OPENAI_API_KEY", "")
GROQ_KEY       = os.environ.get("GROQ_API_KEY", "")
OLLAMA_URL     = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL   = os.environ.get("OLLAMA_MODEL", "llama3")
OPENAI_MODEL   = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
GROQ_MODEL     = os.environ.get("GROQ_MODEL", "llama3-8b-8192")
DEFAULT_BRANCH = os.environ.get("DEFAULT_BRANCH", "main")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SETUP WIZARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ENV_PATH = Path.home() / ".autodeploy.env"

def is_configured() -> bool:
    """Cek apakah sudah ada konfigurasi AI yang valid."""
    provider = os.environ.get("AI_PROVIDER", "")
    if not provider:
        return False
    if provider == "groq" and not os.environ.get("GROQ_API_KEY", ""):
        return False
    if provider == "openai" and not os.environ.get("OPENAI_API_KEY", ""):
        return False
    # ollama tidak butuh API key
    return True


def run_setup_wizard():
    """Setup wizard interaktif untuk konfigurasi pertama kali."""
    ui_clear()
    ui_banner()

    console.print(Panel(
        f"[{C_VAL}]Selamat datang di AutoDeploy AI![/]\n\n"
        f"[{C_DIM}]Sepertinya ini pertama kali kamu menjalankan [/][{C_ACCENT}]autodeploy[/][{C_DIM}].\n"
        f"Setup ini hanya perlu dilakukan sekali.\n"
        f"Konfigurasi akan disimpan di [/][{C_ACCENT}]~/.autodeploy.env[/]",
        title="[bold white] ✦  FIRST TIME SETUP [/]",
        title_align="left",
        border_style=C_ACCENT,
        box=SQUARE,
        padding=(1, 2),
    ))
    console.print()

    # ── Pilih provider ────────────────────────────────────────────────────────
    console.print(f"  [{C_VAL}]Pilih AI provider:[/]\n")
    console.print(f"  [{C_DIM}]1.[/]  [{C_OK}]Groq[/]      [{C_DIM}]— gratis, cepat  (https://console.groq.com/keys)[/]")
    console.print(f"  [{C_DIM}]2.[/]  [{C_ACCENT}]Ollama[/]    [{C_DIM}]— lokal, gratis, tidak perlu API key[/]")
    console.print(f"  [{C_DIM}]3.[/]  [{C_LABEL}]OpenAI[/]    [{C_DIM}]— berbayar       (https://platform.openai.com/api-keys)[/]")
    console.print()

    while True:
        try:
            choice = pt_prompt(
                HTML('<ansibrightblack>  &gt; </ansibrightblack><ansicyan>Provider (1/2/3)  </ansicyan>'),
                style=PT_STYLE,
            ).strip()
        except (KeyboardInterrupt, EOFError):
            raise KeyboardInterrupt

        if choice == "1":
            provider = "groq"
            break
        elif choice == "2":
            provider = "ollama"
            break
        elif choice == "3":
            provider = "openai"
            break
        else:
            ui_warn("Masukkan 1, 2, atau 3.")

    config_lines = [f"AI_PROVIDER={provider}"]

    # ── API key (Groq / OpenAI) ───────────────────────────────────────────────
    if provider == "groq":
        console.print()
        console.print(Panel(
            f"[{C_DIM}]Daftar gratis di [/][{C_ACCENT}]https://console.groq.com/keys[/][{C_DIM}]\n"
            f"lalu buat API key baru dan paste di bawah.[/]",
            border_style=C_DIM, box=SQUARE, padding=(0, 2),
        ))
        console.print()
        while True:
            try:
                key = pt_prompt(
                    HTML('<ansibrightblack>  &gt; </ansibrightblack><ansicyan>Groq API Key  </ansicyan>'),
                    style=PT_STYLE,
                    placeholder="  gsk_...",
                ).strip()
            except (KeyboardInterrupt, EOFError):
                raise KeyboardInterrupt
            if key.startswith("gsk_") and len(key) > 20:
                break
            ui_warn("API key tidak valid. Harus diawali 'gsk_'.")
        config_lines += [
            f"GROQ_API_KEY={key}",
            "GROQ_MODEL=llama-3.1-8b-instant",
        ]

    elif provider == "openai":
        console.print()
        console.print(Panel(
            f"[{C_DIM}]Dapatkan API key di [/][{C_ACCENT}]https://platform.openai.com/api-keys[/]",
            border_style=C_DIM, box=SQUARE, padding=(0, 2),
        ))
        console.print()
        while True:
            try:
                key = pt_prompt(
                    HTML('<ansibrightblack>  &gt; </ansibrightblack><ansicyan>OpenAI API Key  </ansicyan>'),
                    style=PT_STYLE,
                    placeholder="  sk-...",
                ).strip()
            except (KeyboardInterrupt, EOFError):
                raise KeyboardInterrupt
            if key.startswith("sk-") and len(key) > 20:
                break
            ui_warn("API key tidak valid. Harus diawali 'sk-'.")
        config_lines += [
            f"OPENAI_API_KEY={key}",
            "OPENAI_MODEL=gpt-4o-mini",
        ]

    elif provider == "ollama":
        console.print()
        console.print(Panel(
            f"[{C_DIM}]Pastikan Ollama sudah running di lokal.\n"
            f"Download: [/][{C_ACCENT}]https://ollama.com[/]",
            border_style=C_DIM, box=SQUARE, padding=(0, 2),
        ))
        console.print()
        try:
            model = pt_prompt(
                HTML('<ansibrightblack>  &gt; </ansibrightblack><ansicyan>Model name  </ansicyan>'),
                style=PT_STYLE,
                placeholder="  llama3.2:latest",
            ).strip()
        except (KeyboardInterrupt, EOFError):
            raise KeyboardInterrupt
        model = model or "llama3.2:latest"
        config_lines += [
            "OLLAMA_URL=http://localhost:11434",
            f"OLLAMA_MODEL={model}",
        ]

    # ── Simpan ke ~/.autodeploy.env ───────────────────────────────────────────
    config_lines.append("DEFAULT_BRANCH=main")
    ENV_PATH.write_text("\n".join(config_lines) + "\n", encoding="utf-8")

    # ── Reload config ─────────────────────────────────────────────────────────
    _parse_env_file(ENV_PATH)
    global AI_PROVIDER, OPENAI_KEY, GROQ_KEY, OLLAMA_URL, OLLAMA_MODEL, OPENAI_MODEL, GROQ_MODEL
    AI_PROVIDER  = os.environ.get("AI_PROVIDER", "openai")
    OPENAI_KEY   = os.environ.get("OPENAI_API_KEY", "")
    GROQ_KEY     = os.environ.get("GROQ_API_KEY", "")
    OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    GROQ_MODEL   = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

    console.print()
    console.print(Panel(
        f"[{C_OK}]✓  Setup selesai![/]\n\n"
        f"[{C_DIM}]Konfigurasi disimpan di [/][{C_ACCENT}]~/.autodeploy.env[/]\n"
        f"[{C_DIM}]Untuk mengubah, edit file tersebut atau jalankan [/][{C_ACCENT}]autodeploy --setup[/]",
        border_style=C_OK, box=SQUARE, padding=(1, 2),
    ))
    console.print()
    try:
        console.print(f"  [{C_DIM}]Tekan Enter untuk melanjutkan deploy...[/]", end="")
        input()
    except (KeyboardInterrupt, EOFError):
        pass


def run_uninstall():
    """Hapus konfigurasi dan uninstall package autodeploy-ai."""
    ui_clear()
    ui_banner()

    console.print(Panel(
        f"[{C_WARN}]Ini akan menghapus:[/]\n\n"
        f"  [{C_DIM}]•[/]  Config file  [{C_ACCENT}]~/.autodeploy.env[/]\n"
        f"  [{C_DIM}]•[/]  Package      [{C_ACCENT}]autodeploy-ai[/]  (pip uninstall)\n\n"
        f"[{C_DIM}]Command [/][{C_ACCENT}]autodeploy[/][{C_DIM}] tidak akan bisa dipakai lagi.[/]",
        title=f"[bold {C_WARN}] ✦  UNINSTALL [/]",
        title_align="left",
        border_style=C_WARN,
        box=SQUARE,
        padding=(1, 2),
    ))
    console.print()

    try:
        confirm = pt_prompt(
            HTML(f'<ansibrightblack>  &gt; </ansibrightblack><ansiyellow>Yakin? (y/N)  </ansiyellow>'),
            style=PT_STYLE,
        ).strip().lower()
    except (KeyboardInterrupt, EOFError):
        raise KeyboardInterrupt

    if confirm not in ("y", "yes"):
        console.print(f"\n  [{C_DIM}]Uninstall dibatalkan.[/]\n")
        return

    # Hapus config file
    if ENV_PATH.exists():
        ENV_PATH.unlink()
        console.print(f"  [{C_OK}]✓[/]  Config dihapus  [{C_DIM}]{ENV_PATH}[/]")
    else:
        console.print(f"  [{C_DIM}]–[/]  Config tidak ditemukan, dilewati")

    # Uninstall package via pip
    console.print(f"  [{C_DIM}]⠸[/]  Menghapus package autodeploy-ai...", end="\r")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "autodeploy-ai", "-y"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        console.print(f"  [{C_OK}]✓[/]  Package autodeploy-ai dihapus         ")
    else:
        console.print(f"  [{C_ERR}]✗[/]  Gagal uninstall via pip               ")
        console.print(f"  [{C_DIM}]Coba manual: pip uninstall autodeploy-ai[/]")

    console.print()
    console.print(Panel(
        f"[{C_OK}]Uninstall selesai.[/]\n\n"
        f"[{C_DIM}]Terima kasih sudah menggunakan AutoDeploy AI![/]",
        border_style=C_OK, box=SQUARE, padding=(1, 2),
    ))
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UI HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ui_clear():
    os.system("cls" if os.name == "nt" else "clear")


def ui_banner():
    _ensure("pyfiglet")
    import pyfiglet
    fig = pyfiglet.figlet_format("AutoDeploy", font=LOGO, justify="center",
                                  width=console.width or 100)
    console.print()
    console.print(f"[{C_HEAD}]{fig.rstrip()}[/]")
    console.print()
    console.print(Align.center(Text(f"v{APP_VERSION}  ·  Git Init  ·  AI Commit  ·  Auto Push", style=C_DIM)))
    console.print()
    console.print(Align.center(Text("─" * 56, style=C_LINE)))


def ui_splash():
    ui_clear()
    ui_banner()
    labels = ["Initialising", "Reading workspace", "Loading config", "Ready"]
    term_width = os.get_terminal_size().columns if hasattr(os, "get_terminal_size") else 80
    for label in labels:
        text = f"[ {label} ]"
        padded = text.center(term_width)
        sys.stdout.write(f"\033[2K\r{padded}")
        sys.stdout.flush()
        time.sleep(0.15)
    sys.stdout.write("\033[2K\r")
    sys.stdout.flush()


def ui_header(repo_dir: str, branch: str, remote: str, ai_provider: str):
    body = Table.grid(padding=(0, 2))
    body.add_column(justify="right", style=C_LABEL, min_width=10)
    body.add_column(style=C_VAL)

    body.add_row("REMOTE", escape(remote or "not set"))
    body.add_row("BRANCH", f"[{C_ACCENT}]{escape(branch or DEFAULT_BRANCH)}[/]")
    body.add_row("AI", f"[{C_OK}]{ai_provider.upper()}[/]  [{C_DIM}]{_ai_model_label()}[/]")

    console.print(Panel(
        body,
        title="[bold white] SESSION [/]",
        title_align="left",
        border_style=C_LINE,
        box=SQUARE,
        padding=(1, 2),
    ))


def _ai_model_label() -> str:
    if AI_PROVIDER == "openai":
        return OPENAI_MODEL
    if AI_PROVIDER == "groq":
        return GROQ_MODEL
    if AI_PROVIDER == "ollama":
        return OLLAMA_MODEL
    return "unknown"


def ui_success(commit_msg: str, branch: str, remote: str):
    body = Table.grid(padding=(0, 2))
    body.add_column(justify="right", style=C_LABEL, min_width=10)
    body.add_column(style=C_TEXT)
    body.add_row("COMMIT", escape(commit_msg))
    body.add_row("BRANCH", f"[{C_ACCENT}]{escape(branch)}[/]")
    body.add_row("REMOTE", escape(remote))

    console.print()
    console.print(Panel(
        body,
        title=f"[bold {C_OK}] DEPLOY COMPLETE [/]",
        title_align="left",
        border_style=C_OK,
        box=DOUBLE_EDGE,
        padding=(1, 2),
    ))
    console.print()


def ui_error(message: str):
    console.print()
    console.print(Panel(
        f"[{C_TEXT}]{escape(str(message))}[/]",
        title=f"[bold {C_ERR}] ERROR [/]",
        title_align="left",
        border_style=C_ERR,
        box=DOUBLE_EDGE,
        padding=(1, 2),
    ))
    console.print()


def ui_warn(message: str):
    console.print(f"\n  [bold {C_WARN}]![/] [{C_WARN}]{escape(message)}[/]\n")


def ui_step(label: str, value: str = ""):
    val_str = f"  [{C_DIM}]{escape(value)}[/]" if value else ""
    console.print(f"  [{C_ACCENT}]>[/] [{C_TEXT}]{escape(label)}[/]{val_str}")


def ui_tips():
    console.print(Panel(
        f"[{C_LABEL}]Enter[/] [{C_DIM}]terima commit message AI   ·   [/]"
        f"[{C_LABEL}]ketik pesan[/] [{C_DIM}]untuk override   ·   [/]"
        f"[{C_LABEL}]Ctrl+C[/] [{C_DIM}]batal kapan saja[/]",
        border_style=C_DIM,
        box=MINIMAL,
        padding=(0, 1),
    ))
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


def spin_run(cmd: list[str], label: str) -> subprocess.CompletedProcess:
    """Jalankan command sambil tampilkan spinner animasi, lalu print status akhir."""
    import threading
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    stop   = threading.Event()
    result_box: list[subprocess.CompletedProcess] = []

    def _spin():
        i = 0
        while not stop.is_set():
            sys.stdout.write(f"\r  \033[{C_DIM_ANSI}m{frames[i % len(frames)]}\033[0m  {label}...")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:
        result_box.append(subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        ))
    finally:
        stop.set()
        t.join()
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()

    result = result_box[0]
    if result.returncode == 0:
        console.print(f"  [{C_OK}]✓[/]  {label}")
    else:
        console.print(f"  [{C_ERR}]✗[/]  {label}")
    return result


def git_has_changes() -> bool:
    return bool((run(["git", "status", "--porcelain"], capture=True).stdout or "").strip())


def git_current_branch() -> str:
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True)
    return (result.stdout or "").strip() or DEFAULT_BRANCH


def git_remote_url() -> str:
    result = run(["git", "remote", "get-url", "origin"], capture=True)
    return (result.stdout or "").strip()


def git_diff_staged() -> str:
    stat = (run(["git", "diff", "--staged", "--stat"], capture=True).stdout or "").strip()
    diff = (run(["git", "diff", "--staged", "--unified=3"], capture=True).stdout or "").strip()
    MAX = 3500
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


def _call_ollama(diff: str) -> str:
    import urllib.request
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data.get("response", "").strip().strip('"')


def generate_commit_message(diff: str) -> str:
    """Generate AI commit message pakai spinner, lalu user confirm atau override."""
    ai_msg = ""
    stop   = threading.Event()
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def _spin():
        i = 0
        while not stop.is_set():
            sys.stdout.write(f"\r  \033[2m{frames[i % len(frames)]}\033[0m  Generating commit message...")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:
        if AI_PROVIDER == "openai":
            if not OPENAI_KEY:
                raise ValueError("OPENAI_API_KEY tidak ada di .env")
            ai_msg = _call_openai(diff)
        elif AI_PROVIDER == "groq":
            if not GROQ_KEY:
                raise ValueError("GROQ_API_KEY tidak ada di .env")
            ai_msg = _call_groq(diff)
        elif AI_PROVIDER == "ollama":
            ai_msg = _call_ollama(diff)
        else:
            raise ValueError(f"AI provider tidak dikenal: {AI_PROVIDER}")
    except Exception as exc:
        ai_msg = ""
        stop.set()
        t.join()
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()
        console.print(f"  [{C_ERR}]✗[/]  Generating commit message")
        ui_warn(f"AI gagal: {str(exc)}")
    else:
        stop.set()
        t.join()
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()
        if ai_msg:
            console.print(f"  [{C_OK}]✓[/]  Generating commit message")

    if ai_msg:
        console.print()
        console.print(Panel(
            f"[bold {C_TEXT}]{escape(ai_msg)}[/]",
            title="[bold white] SUGGESTED COMMIT [/]",
            title_align="left",
            border_style=C_LINE,
            box=SQUARE,
            padding=(0, 2),
        ))
        console.print()
        try:
            override = pt_prompt(
                HTML('<ansibrightblack>  &gt; </ansibrightblack><ansigreen>commit  </ansigreen>'),
                style=PT_STYLE,
                placeholder="  press Enter to accept, or type your own message",
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
            HTML('<ansibrightblack>  &gt; </ansibrightblack><ansigreen>commit  </ansigreen>'),
            style=PT_STYLE,
            placeholder="  e.g. feat(auth): add login endpoint",
        ).strip()
    except EOFError:
        msg = ""
    except KeyboardInterrupt:
        raise
    return msg


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
            headers={"User-Agent": "AutoDeploy-CLI/1.5"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return True, ""
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, f"Repo tidak ditemukan: [bold]{parts[0]}/{parts[1]}[/bold]\nBuat repo baru di [cyan]https://github.com/new[/cyan] terlebih dahulu."
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
                console.print()
                console.print(Panel(
                    f"[{C_DIM}]Project ini belum punya [/][{C_ACCENT}].git[/][{C_DIM}].[/]\n\n"
                    f"[{C_WARN}]![/] [{C_VAL}]Pastikan kamu sudah membuat repo baru di GitHub terlebih dahulu.[/]\n"
                    f"  [{C_DIM}]Buka [/][{C_ACCENT}]https://github.com/new[/][{C_DIM}] → buat repo → copy URL-nya.[/]\n\n"
                    f"[{C_DIM}]Lalu masukkan URL repo tersebut di bawah.[/]",
                    title="[bold white] NEW REPOSITORY [/]",
                    title_align="left",
                    border_style=C_LINE,
                    box=SQUARE,
                    padding=(1, 2),
                ))
                console.print()
                try:
                    github_url = pt_prompt(
                        HTML('<ansibrightblack>  &gt; </ansibrightblack><ansigreen>github url  </ansigreen>'),
                        style=PT_STYLE,
                        placeholder="  https://github.com/username/repo",
                    ).strip()
                except (KeyboardInterrupt, EOFError):
                    raise KeyboardInterrupt

                if not github_url:
                    ui_warn("URL tidak boleh kosong.")
                    time.sleep(1)
                    continue

            # Validasi repo
            sys.stdout.write(f"\r  \033[2m⠸\033[0m  Checking repository...")
            sys.stdout.flush()
            valid, err_msg = validate_github_url(github_url)
            sys.stdout.write("\r" + " " * 60 + "\r")
            sys.stdout.flush()

            if valid:
                console.print(f"  [{C_OK}]✓[/]  Repository found")
                break
            else:
                # Tampil error, tunggu Enter, lalu ulang dari awal
                console.print()
                console.print(Panel(
                    f"[{C_ERR}]✗  Repo tidak ditemukan[/]\n\n"
                    f"[{C_TEXT}]{err_msg}[/]",
                    border_style=C_ERR,
                    box=SQUARE,
                    padding=(1, 2),
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

        ui_step("git remote add origin", github_url)
        run(["git", "remote", "add", "origin", github_url])
        remote = github_url

    else:
        remote = git_remote_url()
        branch = git_current_branch()

        # Repo ada tapi remote belum di-set
        if not remote:
            if not github_url:
                console.print()
                console.print(Panel(
                    f"[{C_DIM}]Repo ditemukan tapi belum punya remote origin. "
                    f"Masukkan GitHub URL.[/]",
                    title="[bold white] SET REMOTE [/]",
                    title_align="left",
                    border_style=C_LINE,
                    box=SQUARE,
                    padding=(1, 2),
                ))
                console.print()
                try:
                    github_url = pt_prompt(
                        HTML('<ansibrightblack>  &gt; </ansibrightblack><ansigreen>github url  </ansigreen>'),
                        style=PT_STYLE,
                        placeholder="  https://github.com/username/repo",
                    ).strip()
                except (KeyboardInterrupt, EOFError):
                    raise KeyboardInterrupt

            if not github_url:
                ui_error("GitHub URL diperlukan.")
                sys.exit(1)

            ui_step("git remote add origin", github_url)
            run(["git", "remote", "add", "origin", github_url])
            remote = github_url

    branch = git_current_branch()

    # ── Tampilkan header ──────────────────────────────────────────────────────
    ui_clear()
    ui_banner()
    ui_header(cwd, branch, remote, AI_PROVIDER)
    ui_tips()

    # ── Cek perubahan ─────────────────────────────────────────────────────────
    if not git_has_changes():
        console.print(Panel(
            f"[{C_DIM}]Semua file sudah up to date. Tidak ada yang perlu di-commit.[/]",
            title=f"[bold {C_WARN}] NO CHANGES [/]",
            title_align="left",
            border_style=C_WARN,
            box=SQUARE,
            padding=(1, 2),
        ))
        console.print()
        try:
            console.print(f"  [{C_DIM}]Press Enter to exit...[/]", end="")
            input()
        except (KeyboardInterrupt, EOFError):
            pass
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
        ui_error(f"git commit gagal.\n{(result.stderr or '').strip()}")
        sys.exit(1)

    # ── git push ──────────────────────────────────────────────────────────────
    result = spin_run(["git", "push", "-u", "origin", branch], "Pushing to GitHub")
    if result.returncode != 0:
        ui_error(
            f"git push gagal.\n\n"
            f"[{C_DIM}]Kemungkinan penyebab:[/]\n"
            f"- Remote URL salah\n"
            f"- Belum ada akses ke repo\n"
            f"- Branch belum ada di remote\n\n"
            f"[{C_DIM}]{escape((result.stderr or '').strip())}[/]"
        )
        sys.exit(1)

    ui_success(commit_msg, branch, remote)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRYPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main_cli():
    """Entrypoint untuk global CLI command `autodeploy`."""
    args = sys.argv[1:]

    # Flag --setup → paksa jalankan wizard ulang
    if "--setup" in args:
        try:
            run_setup_wizard()
        except KeyboardInterrupt:
            console.print()
            console.print(Align.center(Text("Setup dibatalkan", style=C_DIM)))
            console.print()
        sys.exit(0)

    # Flag --uninstall → hapus config dan uninstall package
    if "--uninstall" in args:
        try:
            run_uninstall()
        except KeyboardInterrupt:
            console.print()
            console.print(Align.center(Text("Uninstall dibatalkan", style=C_DIM)))
            console.print()
        sys.exit(0)

    # Pertama kali — belum dikonfigurasi
    if not is_configured():
        try:
            run_setup_wizard()
        except KeyboardInterrupt:
            console.print()
            console.print(Align.center(Text("─" * 56, style=C_DIM)))
            console.print(Align.center(Text("Setup dibatalkan", style=C_DIM)))
            console.print(Align.center(Text("─" * 56, style=C_DIM)))
            console.print()
            sys.exit(0)

    github_url = args[0] if args and not args[0].startswith("--") else ""
    try:
        deploy(github_url)
    except KeyboardInterrupt:
        console.print()
        console.print(Align.center(Text("─" * 56, style=C_DIM)))
        console.print(Align.center(Text("Deploy dibatalkan", style=C_DIM)))
        console.print(Align.center(Text("─" * 56, style=C_DIM)))
        console.print()
        sys.exit(0)


if __name__ == "__main__":
    main_cli()