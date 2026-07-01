#!/usr/bin/env python3
"""
╭──────────────────────────────────────────────────╮
│           ✦  AutoDeploy CLI  ✦                  │
│     Git Init · AI Commit · Auto Push             │
│                                                  │
│  Requires:                                       │
│    pip install rich prompt_toolkit pyfiglet      │
╰──────────────────────────────────────────────────╯

Usage:
  python deploy.py                            # project sudah punya remote
  python deploy.py https://github.com/u/repo  # project baru, kasih remote-nya
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
_ensure("pyfiglet")

import pyfiglet
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.align import Align
from rich.padding import Padding
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markup import escape
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.formatted_text import HTML

# ── Console ───────────────────────────────────────────────────────────────────
console = Console(highlight=False, soft_wrap=True)

APP_VERSION = "1.0.0"

PT_STYLE = PTStyle.from_dict({
    "prompt":      "bold ansicyan",
    "placeholder": "ansibrightblack",
    "": "ansiwhite",
})

# ── Load .env ─────────────────────────────────────────────────────────────────
def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(
                        key.strip(),
                        value.strip().strip('"').strip("'")
                    )

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
    fig = pyfiglet.figlet_format("AutoDeploy", font="slant")
    console.print()
    for line in fig.strip().splitlines():
        console.print(f"  [bold cyan]{line}[/]")
    console.print()
    console.print(Text("  ✦  Git Init · AI Commit · Auto Push  ✦  ", style="dim white"))
    console.print(Text(f"  v{APP_VERSION}  CLI Edition  ", style="bright_black"))
    console.print()


def ui_splash():
    ui_clear()
    ui_banner()
    steps = [
        ("⠋", "Initialising"),
        ("⠙", "Reading workspace"),
        ("⠹", "Loading config"),
        ("⠸", "Ready"),
    ]
    for ch, label in steps:
        console.print(f"  [bright_black]{ch}[/]  [dim]{label}...[/]", end="\r")
        time.sleep(0.2)
    console.print(" " * 40, end="\r")


def ui_rule(label: str = ""):
    if label:
        console.print(Rule(f"[bright_black]{label}[/]", style="bright_black"))
    else:
        console.print(Rule(style="bright_black"))


def ui_header(repo_dir: str, branch: str, remote: str, ai_provider: str):
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bright_black", min_width=12)
    grid.add_column()

    grid.add_row("Directory", f"[dodger_blue1]{escape(repo_dir)}[/]")
    grid.add_row("Branch",    f"[cyan]{escape(branch or DEFAULT_BRANCH)}[/]")
    grid.add_row("Remote",    f"[white]{escape(remote or 'not set')}[/]")
    grid.add_row("AI",        f"[green]{ai_provider.upper()}[/]  [bright_black]({_ai_model_label()})[/]")

    title = Text.from_markup("  [bold cyan]✦[/]  [bold white]AutoDeploy CLI[/]  [bold cyan]✦[/]  ")
    panel = Panel(
        Padding(grid, (0, 1)),
        title=title,
        subtitle=Text.from_markup("[bright_black]Git Init · AI Commit · Auto Push[/]"),
        border_style="bright_black",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)


def _ai_model_label() -> str:
    if AI_PROVIDER == "openai":
        return OPENAI_MODEL
    if AI_PROVIDER == "groq":
        return GROQ_MODEL
    if AI_PROVIDER == "ollama":
        return OLLAMA_MODEL
    return "unknown"


def ui_success(commit_msg: str, branch: str, remote: str):
    console.print()
    console.print(Panel(
        f"[bold green]✓  Deploy Complete[/]\n\n"
        f"[bright_black]Commit [/] [white]{escape(commit_msg)}[/]\n"
        f"[bright_black]Branch [/] [cyan]{escape(branch)}[/]\n"
        f"[bright_black]Remote [/] [dodger_blue1]{escape(remote)}[/]",
        border_style="green",
        padding=(1, 2),
    ))
    console.print()


def ui_error(message: str):
    console.print()
    console.print(Panel(
        f"[bold bright_red]✗  Error[/]\n\n[white]{escape(str(message))}[/]",
        border_style="bright_red",
        padding=(1, 2),
    ))
    console.print()


def ui_warn(message: str):
    console.print(f"\n  [bold yellow]⚠[/]  [yellow]{escape(message)}[/]\n")


def ui_step(icon: str, label: str, value: str = ""):
    val_str = f"  [bright_black]{escape(value)}[/]" if value else ""
    console.print(f"  [cyan]{icon}[/]  [white]{escape(label)}[/]{val_str}")


def ui_tips():
    tips = [
        "[bright_black]•[/] [dim]Tekan[/] [cyan]Enter[/] [dim]untuk konfirmasi commit message AI[/]",
        "[bright_black]•[/] [dim]Ketik pesan baru untuk override commit message[/]",
        "[bright_black]•[/] [dim]Ctrl+C untuk batal kapan saja[/]",
    ]
    console.print()
    for tip in tips:
        console.print(f"    {tip}")
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
        SpinnerColumn("dots", style="cyan"),
        TextColumn(f"[dim]Generating commit message via [bold]{AI_PROVIDER.upper()}[/]...[/]"),
        console=console,
        transient=True,
    ) as pg:
        pg.add_task("")
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
            console.print(f"\n  [yellow]⚠[/]  [dim]AI gagal: {escape(str(exc))}[/]")

    if ai_msg:
        console.print()
        console.print(Panel(
            f"[bright_black]Suggested[/]\n\n[bold white]{escape(ai_msg)}[/]",
            title="[bold cyan]✦  AI Commit Message[/]",
            border_style="bright_black",
            padding=(1, 2),
        ))
        console.print()
        try:
            override = pt_prompt(
                HTML('<ansibrightblack>  ❯ </ansibrightblack><ansicyan>Commit  </ansicyan>'),
                style=PT_STYLE,
                placeholder="  press Enter to accept, or type your own message",
            ).strip()
        except (KeyboardInterrupt, EOFError):
            return ai_msg
        return override if override else ai_msg

    # AI failed — manual fallback
    ui_warn("AI tidak bisa generate commit message. Masukkan manual:")
    try:
        msg = pt_prompt(
            HTML('<ansibrightblack>  ❯ </ansibrightblack><ansicyan>Commit  </ansicyan>'),
            style=PT_STYLE,
            placeholder="  e.g. feat(auth): add login endpoint",
        ).strip()
    except (KeyboardInterrupt, EOFError):
        msg = ""
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
                "[dim]Project ini belum punya [/][cyan].git[/][dim]. "
                "Masukkan GitHub URL untuk dijadikan remote origin.[/]",
                title="[bold white]🔗  New Repository[/]",
                border_style="bright_black",
                padding=(1, 2),
            ))
            console.print()
            try:
                github_url = pt_prompt(
                    HTML('<ansibrightblack>  ❯ </ansibrightblack><ansicyan>GitHub URL  </ansicyan>'),
                    style=PT_STYLE,
                    placeholder="  https://github.com/username/repo",
                ).strip()
            except (KeyboardInterrupt, EOFError):
                github_url = ""

        if not github_url:
            ui_error("GitHub URL diperlukan untuk repo baru.")
            sys.exit(1)

        ui_step("⠸", "git init")
        run(["git", "init"])
        run(["git", "checkout", "-b", DEFAULT_BRANCH])

        ui_step("⠸", "git remote add origin", github_url)
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
                    "[dim]Repo ditemukan tapi belum punya remote origin. "
                    "Masukkan GitHub URL.[/]",
                    title="[bold white]🔗  Set Remote[/]",
                    border_style="bright_black",
                    padding=(1, 2),
                ))
                console.print()
                try:
                    github_url = pt_prompt(
                        HTML('<ansibrightblack>  ❯ </ansibrightblack><ansicyan>GitHub URL  </ansicyan>'),
                        style=PT_STYLE,
                        placeholder="  https://github.com/username/repo",
                    ).strip()
                except (KeyboardInterrupt, EOFError):
                    github_url = ""

            if not github_url:
                ui_error("GitHub URL diperlukan.")
                sys.exit(1)

            ui_step("⠸", "git remote add origin", github_url)
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
            "[bold yellow]⚠  Tidak ada perubahan[/]\n\n"
            "[dim]Semua file sudah up to date. Tidak ada yang perlu di-commit.[/]",
            border_style="yellow",
            padding=(1, 2),
        ))
        console.print()
        sys.exit(0)

    # ── git add . ─────────────────────────────────────────────────────────────
    ui_step("●", "Staging semua perubahan", "git add .")
    run(["git", "add", "."])

    # ── Ambil diff ────────────────────────────────────────────────────────────
    diff = git_diff_staged()

    # ── AI commit message ─────────────────────────────────────────────────────
    commit_msg = generate_commit_message(diff)
    if not commit_msg:
        ui_error("Commit message kosong. Deploy dibatalkan.")
        sys.exit(1)

    # ── git commit ────────────────────────────────────────────────────────────
    ui_step("●", "Committing", commit_msg)
    result = run(["git", "commit", "-m", commit_msg])
    if result.returncode != 0:
        ui_error(f"git commit gagal.\n{result.stderr}")
        sys.exit(1)

    # ── git push ──────────────────────────────────────────────────────────────
    console.print()
    with Progress(
        TextColumn("  "),
        SpinnerColumn("dots", style="cyan"),
        TextColumn(f"[dim]Pushing ke[/] [cyan]{escape(branch)}[/][dim]...[/]"),
        console=console,
        transient=True,
    ) as pg:
        pg.add_task("")
        result = run(["git", "push", "-u", "origin", branch])

    if result.returncode != 0:
        ui_error(
            f"git push gagal.\n\n"
            f"[dim]Kemungkinan penyebab:[/]\n"
            f"• Remote URL salah\n"
            f"• Belum ada akses ke repo\n"
            f"• Branch belum ada di remote (coba push manual sekali)\n\n"
            f"[bright_black]{escape((result.stderr or '').strip())}[/]"
        )
        sys.exit(1)

    ui_success(commit_msg, branch, remote)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRYPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    github_url = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        deploy(github_url)
    except KeyboardInterrupt:
        console.print()
        console.print(Rule(style="bright_black"))
        console.print(
            Align.center(Text("  ✦  Deploy dibatalkan  ✦  ", style="dim white"))
        )
        console.print(Rule(style="bright_black"))
        console.print()
        sys.exit(0)
