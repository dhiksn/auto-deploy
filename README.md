# ✦ AutoDeploy CLI

> Git Init · AI Commit · Auto Push — dari terminal mana pun, satu command.

---

## Fitur

- **Auto `git init`** kalau project belum punya `.git`
- **Set remote otomatis** dari GitHub URL yang lo kasih
- **AI generate commit message** pakai Ollama, OpenAI, atau Groq
- **Auto `git add` + `git push`** setelah commit
- **Global CLI** — bisa dipanggil dari folder project mana pun tanpa copy file

---

## Install

```bash
pip install -e "path/to/auto-deploy"
```

Setelah install, command `deploy` langsung tersedia global.

---

## Setup

Copy `.env.example` jadi `.env` lalu isi sesuai provider AI yang lo pakai:

```bash
cp .env.example .env
```

```env
# Pilih provider: openai | groq | ollama
AI_PROVIDER=ollama

OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# OPENAI_API_KEY=sk-...
# GROQ_API_KEY=gsk_...
```

---

## Cara Pakai

```bash
# Project baru — belum ada .git
deploy https://github.com/username/repo-name

# Project yang sudah punya remote
deploy
```

### Flow yang terjadi

```
1. Cek .git
   ├── Belum ada → git init + git remote add origin <url>
   └── Sudah ada → cek remote, minta URL kalau belum ada

2. git add .

3. AI generate commit message
   └── Tekan Enter untuk pakai, atau ketik manual untuk override

4. git commit -m "<pesan>"

5. git push -u origin <branch>
```

---

## Provider AI

| Provider | Keterangan | API Key |
|---|---|---|
| `ollama` | Lokal, gratis, butuh Ollama running | Tidak perlu |
| `groq` | Online, gratis, cepat | [console.groq.com](https://console.groq.com) |
| `openai` | GPT-4o-mini | [platform.openai.com](https://platform.openai.com) |

---

## Requirements

- Python 3.10+
- Git
- Salah satu AI provider di atas
