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

APP_VERSION = "1.0.0"

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

PT_STYLE = PTStyle.from_dict({
    "prompt":      "bold ansigreen",
    "placeholder": "ansibrightblack",
    "": "ansiwhite",
})

LOGO = "small"  # pyfiglet font

# ── Load .env ─────────────────────────────────────────────────────────────────
def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    # Selalu override dari .env, jangan pakai setdefault
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

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
#  UI HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ui_clear():
    os.system("cls" if os.name == "nt" else "clear")


def ui_banner():
    _ensure("pyfiglet")
    import pyfiglet
    fig = pyfiglet.figlet_format("AutoDeploy", font=LOGO)
    console.print()
    for line in fig.strip("\n").splitlines():
        console.print(Align.center(Text(line, style=C_HEAD)))
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

    body.add_row("DIR", escape(repo_dir))
    body.add_row("BRANCH", f"[{C_ACCENT}]{escape(branch or DEFAULT_BRANCH)}[/]")
    body.add_row("REMOTE", escape(remote or "not set"))
    body.add_row("AI", f"[{C_OK}]{ai_provider.upper()}[/]  [{C_DIM}]{_ai_model_label()}[/]")

    console.print()
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
    console.print()
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
    """Generate AI commit message, then let user confirm or override."""
    ai_msg = ""

    with Progress(
        TextColumn("  "),
        BarColumn(bar_width=20, style=C_DIM, complete_style=C_ACCENT, finished_style=C_OK),
        TextColumn(f"[{C_LABEL}]{AI_PROVIDER.upper()} thinking...[/]"),
        console=console,
        transient=True,
    ) as pg:
        pg.add_task("", total=None)
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
            console.print(f"\n  [{C_WARN}]![/] [{C_DIM}]AI gagal: {escape(str(exc))}[/]")

    if ai_msg:
        console.print()
        console.print(Panel(
            f"[bold {C_TEXT}]{escape(ai_msg)}[/]",
            title="[bold white] SUGGESTED COMMIT [/]",
            title_align="left",
            border_style=C_LINE,
            box=SQUARE,
            padding=(1, 2),
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
            raise  # naik ke main_cli, stop deploy
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
        raise  # naik ke main_cli, stop deploy
    return msg


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
        if not github_url:
            console.print()
            console.print(Panel(
                f"[{C_DIM}]Project ini belum punya [/][{C_ACCENT}].git[/][{C_DIM}]. "
                f"Masukkan GitHub URL untuk dijadikan remote origin.[/]",
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
        sys.exit(0)

    # ── git add . ─────────────────────────────────────────────────────────────
    ui_step("Staging semua perubahan", "git add .")
    result = run(["git", "add", "."], capture=True)
    # Print warning dari git add dengan indent yang sejajar
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    if output:
        for line in output.splitlines():
            console.print(f"  [{C_DIM}]{escape(line)}[/]")

    # ── Ambil diff ────────────────────────────────────────────────────────────
    diff = git_diff_staged()

    # ── AI commit message ─────────────────────────────────────────────────────
    commit_msg = generate_commit_message(diff)
    if not commit_msg:
        ui_error("Commit message kosong. Deploy dibatalkan.")
        sys.exit(1)

    # ── git commit ────────────────────────────────────────────────────────────
    ui_step("Committing", commit_msg)
    result = run(["git", "commit", "-m", commit_msg])
    if result.returncode != 0:
        ui_error(f"git commit gagal.\n{result.stderr}")
        sys.exit(1)

    # ── git push ──────────────────────────────────────────────────────────────
    console.print()
    with Progress(
        TextColumn("  "),
        BarColumn(bar_width=20, style=C_DIM, complete_style=C_ACCENT, finished_style=C_OK),
        TextColumn(f"[{C_LABEL}]pushing to {escape(branch)}...[/]"),
        console=console,
        transient=True,
    ) as pg:
        pg.add_task("", total=None)
        result = run(["git", "push", "-u", "origin", branch])

    if result.returncode != 0:
        ui_error(
            f"git push gagal.\n\n"
            f"[{C_DIM}]Kemungkinan penyebab:[/]\n"
            f"- Remote URL salah\n"
            f"- Belum ada akses ke repo\n"
            f"- Branch belum ada di remote (coba push manual sekali)\n\n"
            f"[{C_DIM}]{escape((result.stderr or '').strip())}[/]"
        )
        sys.exit(1)

    ui_success(commit_msg, branch, remote)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRYPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main_cli():
    """Entrypoint untuk global CLI command `deploy`."""
    github_url = sys.argv[1] if len(sys.argv) > 1 else ""
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