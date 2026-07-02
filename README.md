# ✦ AutoDeploy CLI

> Git Init · AI Commit · Auto Push — dari terminal mana pun, satu command.

---

## Fitur

- **Auto `git init`** kalau project belum punya `.git`
- **Set remote otomatis** dari GitHub URL yang lo kasih
- **AI generate commit message** pakai Groq, OpenAI, atau Ollama
- **Spinner animasi** di tiap step — staging, generating, commit, push
- **Global CLI** — bisa dipanggil dari folder project mana pun tanpa copy file

---

## Install

Clone repo ini, lalu install sebagai global command:

```bash
git clone https://github.com/dhiksn/auto-deploy.git
cd auto-deploy
pip install -e .
```

Setelah install, command `deploy` langsung tersedia dari terminal mana pun.  
Dependencies (`rich`, `prompt_toolkit`, `pyfiglet`) diinstall otomatis.

---

## Setup

Buat file `.env` dari contoh yang tersedia:

```bash
# Windows
copy .env.example .env

# Linux / Mac
cp .env.example .env
```

Edit `.env` sesuai provider AI yang lo pakai:

```env
# Pilih provider: groq | openai | ollama
AI_PROVIDER=groq

# Groq (gratis, cepat) — https://console.groq.com/keys
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-8b-instant

# Ollama (lokal, tidak perlu API key)
# OLLAMA_URL=http://localhost:11434
# OLLAMA_MODEL=llama3.2:latest

# OpenAI
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini
```

> **Penting:** file `.env` sudah di-ignore git. Jangan pernah commit file ini karena berisi API key.

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
  ⠙  Staging changes         → git add .
  ⠙  Generating commit message  → AI generate via Groq / OpenAI / Ollama
                                   └─ konfirmasi atau ketik manual
  ⠙  Creating commit         → git commit -m "<pesan>"
  ⠙  Pushing to GitHub       → git push -u origin <branch>
```

Kalau project belum ada `.git`, sebelum flow di atas akan otomatis:
- `git init`
- `git remote add origin <url>`

---

## Provider AI

| Provider | Model | Keterangan | API Key |
|---|---|---|---|
| `groq` | `llama-3.1-8b-instant` | Online, gratis, cepat | [console.groq.com](https://console.groq.com/keys) |
| `ollama` | `llama3.2:latest` | Lokal, gratis, butuh Ollama running | Tidak perlu |
| `openai` | `gpt-4o-mini` | Online, berbayar | [platform.openai.com](https://platform.openai.com/api-keys) |

Untuk ganti provider, ubah `AI_PROVIDER` di file `.env`.

---

## Requirements

- Python 3.10+
- Git
- Salah satu AI provider di atas
