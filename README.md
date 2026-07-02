# ✦ AutoDeploy AI

> Git Init · AI Commit · Auto Push — dari terminal mana pun, satu command.

AutoDeploy AI adalah CLI yang mengotomatisasi proses deploy project ke GitHub:
- Git init otomatis
- AI generate commit message
- Push ke GitHub dalam satu command

**Setup — masukin URL repo GitHub buat pertama kali:**
![Setup deploy](https://raw.githubusercontent.com/dhiksn/auto-deploy/main/Tawal.png)

**Setelah jalan — cek status repo & AI commit:**
![Deploy running](https://raw.githubusercontent.com/dhiksn/auto-deploy/main/Takhir.png)

---

## Fitur

- **Auto `git init`** kalau project belum punya `.git`
- **Set remote otomatis** dari GitHub URL yang lo kasih
- **Validasi repo** — cek apakah repo GitHub benar-benar ada sebelum deploy
- **AI generate commit message** pakai Groq, OpenAI, atau Ollama
- **Spinner animasi** di tiap step — staging, generating, commit, push
- **Global CLI** — bisa dipanggil dari folder project mana pun tanpa copy file

---

## Install

```bash
pip install autodeploy-ai
```

Setelah install, command `autodeploy` langsung tersedia dari terminal mana pun.

---

## Setup

Buat file `.env` di folder manapun lo mau deploy, atau di home directory:

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

> **Penting:** jangan pernah commit file `.env` karena berisi API key.

---

## Cara Pakai

```bash
# Project baru — belum ada .git
autodeploy https://github.com/username/repo-name

# Project yang sudah punya remote
autodeploy
```

### Flow yang terjadi

```
  ✓  Staging changes            → git add .
  ✓  Generating commit message  → AI generate via Groq / OpenAI / Ollama
                                   └─ konfirmasi atau ketik manual
  ✓  Creating commit            → git commit -m "<pesan>"
  ✓  Pushing to GitHub          → git push -u origin <branch>
```

Kalau project belum ada `.git`, sebelum flow di atas akan otomatis:
1. Validasi repo GitHub — pastiin sudah dibuat di [github.com/new](https://github.com/new)
2. `git init`
3. `git remote add origin <url>`

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
