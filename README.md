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

Clone repo ini, lalu install sebagai global command:

```bash
git clone https://github.com/dhiksn/auto-deploy.git
cd auto-deploy
pip install -e .
```

Setelah install, command `deploy` langsung tersedia dari terminal mana pun.

---

## Setup

Copy `.env.example` jadi `.env` lalu isi sesuai provider AI yang lo pakai:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Pilih provider: openai | groq | ollama
AI_PROVIDER=groq

# Groq (gratis, cepat)
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-8b-instant

# Ollama (lokal)
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

| Provider | Model | Keterangan | API Key |
|---|---|---|---|
| `groq` | `llama-3.1-8b-instant` | Online, gratis, cepat | [console.groq.com](https://console.groq.com/keys) |
| `ollama` | `llama3.2:latest` | Lokal, gratis, butuh Ollama running | Tidak perlu |
| `openai` | `gpt-4o-mini` | Online, berbayar | [platform.openai.com](https://platform.openai.com/api-keys) |

Untuk ganti provider, tinggal ubah `AI_PROVIDER` di file `.env`.

---

## Requirements

- Python 3.10+
- Git
- Salah satu AI provider di atas
