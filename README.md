# ✦ AutoDeploy AI

> Git Init · AI Commit · Auto Push — dari terminal mana pun, satu command.

AutoDeploy AI adalah CLI yang mengotomatisasi proses deploy project ke GitHub:
- Git init otomatis
- AI generate commit message
- Push ke GitHub dalam satu command

**Tampilan Awal**
![Setup deploy](https://raw.githubusercontent.com/dhiksn/auto-deploy/main/Tawal.png)

**Tampilan Akhir**
![Deploy running](https://raw.githubusercontent.com/dhiksn/auto-deploy/main/Takhir.png)

---

## Fitur

- **Auto `git init`** kalau project belum punya `.git`
- **Set remote otomatis** dari GitHub URL yang lo kasih
- **Validasi repo** — cek apakah repo GitHub benar-benar ada sebelum deploy
- **AI generate commit message** pakai Groq, OpenAI, atau Ollama
- **Spinner animasi** di tiap step — staging, generating, commit, push
- **Setup wizard** — pertama kali jalan langsung guided setup, tidak perlu config manual
- **Global CLI** — bisa dipanggil dari folder project mana pun

---

## Install

```bash
pip install autodeploy-ai
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

---

## Setup Wizard

Saat pertama kali jalan, wizard akan memandu:

```
✦  FIRST TIME SETUP

Pilih AI provider:
  1.  Groq    — gratis, cepat
  2.  Ollama  — lokal, gratis, tidak perlu API key
  3.  OpenAI  — berbayar

> Provider (1/2/3)
> Groq API Key   gsk_...

✓  Setup selesai! Disimpan di ~/.autodeploy.env
```

---

## Flow Deploy

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

---