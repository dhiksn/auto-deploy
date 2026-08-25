# ✦ AutoDeploy AI

> Git Init · AI Commit · Auto Push — dari terminal mana pun, satu command.

AutoDeploy AI adalah CLI yang mengotomatisasi proses deploy project ke GitHub:
- Git init otomatis
- AI generate commit message
- Push ke GitHub dalam satu command
   
**Tampilan Awal**
![Setup deploy](https://raw.githubusercontent.com/dhiksn/auto-deploy/main/Tawal.png)

---

## Fitur

- **Auto `git init`** kalau project belum punya `.git`
- **Set remote otomatis** dari GitHub URL yang lo kasih
- **Validasi repo** — cek apakah repo GitHub benar-benar ada sebelum deploy
- **AI generate commit message** pakai OpenRouter, Groq, OpenAI, atau Ollama
- **Spinner animasi** di tiap step — staging, generating, commit, push
- **Setup wizard** — pertama kali jalan langsung guided setup, tidak perlu config manual
- **Global CLI** — bisa dipanggil dari folder project mana pun
- **Auto clear credential** — kalau push gagal karena akun GitHub beda, credential lama otomatis dihapus dan Git akan minta login ulang

---

## Install

```bash
pip install autodeploy-ai --upgrade --no-cache-dir
```

Setelah install, command `autodeploy` langsung tersedia dari terminal mana pun.

---

## Cara Pakai

```bash
# Project baru — belum ada .git
autodeploy https://github.com/username/repo-name

# Project yang sudah punya remote
autodeploy
```

Pertama kali menjalankan `autodeploy`, wizard setup akan otomatis muncul untuk mengatur provider AI dan API key. Konfigurasi disimpan di `~/.autodeploy.env` dan berlaku dari folder mana pun.

Untuk mengubah konfigurasi:

```bash
autodeploy --setup
```

Untuk uninstall semuanya:

```bash
autodeploy --uninstall
```

**Tampilan Uninstall**
![Uninstall Package](https://raw.githubusercontent.com/dhiksn/auto-deploy/main/uninstall.png)

---

## Setup Wizard

Saat pertama kali jalan, wizard akan memandu memilih provider AI dan memasukkan API key:

```
✦  FIRST TIME SETUP

Pilih AI provider:
  1.  OpenRouter — gratis, 20+ model
  2.  Groq       — gratis, cepat
  3.  Ollama     — lokal, offline, tidak perlu API key
  4.  OpenAI     — berbayar

> Provider (1/2/3/4)
> OpenRouter API Key   sk-or-...

✓  Setup selesai! Disimpan di ~/.autodeploy.env
```

---

## Flow Deploy

```
  ✓  Staging changes            → git add .
  ✓  Generating commit message  → AI generate via OpenRouter / Groq / OpenAI / Ollama
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

| Provider | Model Default | Keterangan | API Key |
|---|---|---|---|
| `openrouter` | `google/gemma-4-31b-it:free` | Online, gratis, 20+ model tersedia | [openrouter.ai](https://openrouter.ai) |
| `groq` | `llama-3.3-70b-versatile` | Online, gratis, cepat | [console.groq.com](https://console.groq.com/keys) |
| `ollama` | `llama3.2:latest` | Lokal, gratis, butuh Ollama running | Tidak perlu |
| `openai` | `gpt-4o-mini` | Online, berbayar | [platform.openai.com](https://platform.openai.com/api-keys) |

Model bisa diganti manual di `~/.autodeploy.env`:

```env
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=google/gemma-4-31b-it:free
```

Model OpenRouter gratis lainnya yang bisa dipakai:
- `nvidia/nemotron-3.5-lightning:free`
- `google/gemma-4-26b-a4b-it:free`
- `minimax/minimax-m3:free`

---

## Multi Akun GitHub

Kalau `git push` gagal karena akun GitHub yang aktif berbeda dengan pemilik repo, AutoDeploy akan otomatis:

1. Mendeteksi error autentikasi (401 / 403 / authentication failed)
2. Menghapus credential GitHub lama dari sistem
3. Menampilkan panduan login ulang dengan akun yang benar
4. Retry push — Git akan meminta login ulang secara otomatis

> Gunakan **Personal Access Token** sebagai password saat login ulang.  
> Buat token di: [github.com/settings/tokens](https://github.com/settings/tokens)

---

## Konfigurasi Lengkap

Semua konfigurasi disimpan di `~/.autodeploy.env`:

```env
# Provider: openrouter | groq | ollama | openai
AI_PROVIDER=openrouter

OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=google/gemma-4-31b-it:free

GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

DEFAULT_BRANCH=main
```

---
