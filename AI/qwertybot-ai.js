/**
 * PROJECT      : QwertyBot AI 
 * AUTHOR       : BINTANG
 * CREATOR      : BINTANG
 * DESC         : Scraper AI multimodal qwertybot.biz.id — support chat,
 *                upload gambar, 
 *                session.
 * USAGE        : node qwertybot.js "prompt" [options]
 *                node qwertybot.js "Jelaskan async JavaScript"
 *                node qwertybot.js --model pro "Buat fibonacci"
 *                node qwertybot.js --image foto.jpg "Analisa gambar"
 *                node qwertybot.js --multi
 */

'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const CONFIG = Object.freeze({
  BASE_URL: 'https://qwertybot.biz.id',
  ENDPOINTS: {
    SESSION: '/api/sessions/new',
    CHAT: '/api/chat',
  },
  DEFAULT_MODEL: 'flash',
  MODELS: {
    flash: 'gemini-flash-lite-latest',
    turbo: 'gemini-3.1-flash-lite',
    pro: 'gemini-3.1-pro-preview',
  },
  UA: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  TIMEOUT_MS: 90000,
  MAX_RETRY: 3,
  RETRY_DELAY_MS: 2000,
  RETRYABLE_STATUS: [429, 500, 502, 503, 504],
  SESSION_TITLE: 'Percakapan Baru',
});

class QwertyBotError extends Error {
  constructor(message, code = 'UNKNOWN', meta = {}) {
    super(message);
    this.name = 'QwertyBotError';
    this.code = code;
    this.meta = meta;
  }
}

const Utils = {
  genId() {
    return crypto.randomBytes(6).toString('hex');
  },

  genOwnerId() {
    const rand = Math.random().toString(36).slice(2, 10);
    return `guest_${rand}${Date.now().toString(36)}`;
  },

  resolveModel(input) {
    if (!input) return CONFIG.MODELS[CONFIG.DEFAULT_MODEL];
    if (CONFIG.MODELS[input]) return CONFIG.MODELS[input];
    if (Object.values(CONFIG.MODELS).includes(input)) return input;
    throw new QwertyBotError(`Model tidak dikenal: ${input}`, 'INVALID_MODEL', {
      available: Object.keys(CONFIG.MODELS),
    });
  },

  fileToBlob(filepath) {
    if (!fs.existsSync(filepath)) {
      throw new QwertyBotError(`File gak ada: ${filepath}`, 'FILE_NOT_FOUND');
    }
    const buf = fs.readFileSync(filepath);
    const name = path.basename(filepath);
    const ext = path.extname(filepath).toLowerCase().slice(1);
    const mimeMap = {
      jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png',
      gif: 'image/gif', webp: 'image/webp', pdf: 'application/pdf',
      txt: 'text/plain', json: 'application/json',
    };
    const type = mimeMap[ext] || 'application/octet-stream';
    return { buffer: buf, filename: name, type };
  },

  async sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  },

  formatQuota(raw) {
    if (!raw || typeof raw !== 'object') return null;

    const limit = raw.maxQuota ?? 0;
    const used = raw.usedCount ?? 0;
    const left = raw.remaining ?? Math.max(0, limit - used);
    const pct = limit > 0 ? Math.round((used / limit) * 100) : 0;

    let health = 'good';
    if (raw.isExhausted || left <= 0) health = 'empty';
    else if (pct >= 75) health = 'warn';

    return {
      tier: raw.isLoggedIn ? 'member' : 'guest',
      limit,
      used,
      left,
      pct_used: pct,
      health,
      depleted: !!raw.isExhausted,
      refresh_at: raw.resetAt ?? null,
      refresh_in: raw.resetInSeconds ?? null,
      refresh_label: raw.formattedResetTime ?? null,
    };
  },

  buildResponse(fields = {}) {
    const {
      status = 'ok',
      data = null,
      error = null,
      meta = {},
      requestId = null,
      quota = null,
    } = fields;

    const response = {
      status,
      by: 'BINTANG',
      ts: new Date().toISOString(),
      request_id: requestId || Utils.genId(),
      meta: {
        duration_ms: meta.durationMs ?? 0,
        turn: meta.turn ?? 1,
        session: meta.sessionId || null,
        owner: meta.ownerId || null,
        model: meta.model || null,
        model_alias: meta.modelAlias || null,
        retries: meta.retries ?? 0,
        history: meta.historyLength ?? 0,
      },
    };

    if (status === 'ok') {
      response.data = data || {};
      if (quota) response.quota = quota;
    } else {
      response.fault = {
        code: error?.code || 'UNKNOWN',
        message: error?.message || 'Unknown error',
        details: error?.meta || null,
      };
    }

    return response;
  },
};

class QwertyBot {
  constructor(opts = {}) {
    this.model = Utils.resolveModel(opts.model);
    this.modelAlias = opts.model || CONFIG.DEFAULT_MODEL;
    this.ownerId = opts.ownerId || Utils.genOwnerId();
    this.sessionId = opts.sessionId || null;
    this.sessionCode = opts.sessionCode || null;
    this.retry = opts.retry ?? CONFIG.MAX_RETRY;
    this.history = [];
    this.quota = null;
    this._retryCount = 0;
  }

  get hasSession() {
    return !!(this.sessionId && this.sessionCode);
  }

  get turn() {
    return Math.floor(this.history.length / 2) + 1;
  }

  async createSession() {
    const res = await this._fetch(CONFIG.ENDPOINTS.SESSION, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': CONFIG.UA,
      },
      body: JSON.stringify({
        title: CONFIG.SESSION_TITLE,
        ownerId: this.ownerId,
      }),
    });

    const rawText = await res.text();
    let data = null;
    try { data = JSON.parse(rawText); } catch {}

    if (!res.ok || !data?.success || !data?.session) {
      throw new QwertyBotError(
        `Gagal bikin session: ${data ? JSON.stringify(data) : rawText.slice(0, 200)}`,
        'SESSION_FAILED',
        { status: res.status }
      );
    }

    this.sessionId = data.session.id;
    this.sessionCode = data.session.sessionCode;

    return { id: this.sessionId, code: this.sessionCode };
  }

  async ensureSession() {
    if (!this.hasSession) await this.createSession();
    return { id: this.sessionId, code: this.sessionCode };
  }

  resetSession() {
    this.sessionId = null;
    this.sessionCode = null;
    this.history = [];
    this._retryCount = 0;
  }

  async _fetch(url, opts = {}, attempt = 1) {
    const fullUrl = url.startsWith('http') ? url : CONFIG.BASE_URL + url;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), CONFIG.TIMEOUT_MS);

    try {
      const res = await fetch(fullUrl, { ...opts, signal: controller.signal });
      clearTimeout(timer);

      if (CONFIG.RETRYABLE_STATUS.includes(res.status) && attempt < this.retry) {
        this._retryCount = attempt;
        try { await res.text(); } catch {}
        await Utils.sleep(CONFIG.RETRY_DELAY_MS * attempt);
        return this._fetch(url, opts, attempt + 1);
      }

      return res;
    } catch (err) {
      clearTimeout(timer);
      const isTimeout = err.name === 'AbortError' || /timeout/i.test(err.message);

      if (isTimeout && attempt < this.retry) {
        this._retryCount = attempt;
        await Utils.sleep(CONFIG.RETRY_DELAY_MS * attempt);
        return this._fetch(url, opts, attempt + 1);
      }

      throw new QwertyBotError(
        isTimeout
          ? `Request timeout setelah ${CONFIG.TIMEOUT_MS}ms (${attempt}x percobaan)`
          : `Fetch error: ${err.message}`,
        isTimeout ? 'TIMEOUT' : 'FETCH_ERROR',
        { attempt, url: fullUrl }
      );
    }
  }

  _buildForm(message, files = []) {
    const form = new FormData();
    form.append('sessionId', this.sessionId);
    form.append('sessionCode', this.sessionCode);
    form.append('message', message);
    form.append('ownerId', this.ownerId);
    form.append('isLoggedIn', 'false');
    form.append('selectedModel', this.model);
    form.append('adminToken', '');

    for (const item of files) {
      if (item.buffer) {
        const blob = new Blob([item.buffer], {
          type: item.type || 'application/octet-stream',
        });
        form.append('files', blob, item.filename || 'file');
      }
    }
    return form;
  }

  async ask(message, opts = {}) {
    const { files = [], keepHistory = true, requestId = null } = opts;

    if (!message || typeof message !== 'string') {
      throw new QwertyBotError('Message harus string non-kosong', 'INVALID_MESSAGE');
    }

    await this.ensureSession();

    const startTime = Date.now();
    const currentTurn = this.turn;
    const reqId = requestId || Utils.genId();

    const form = this._buildForm(message, files);
    const res = await this._fetch(CONFIG.ENDPOINTS.CHAT, {
      method: 'POST',
      headers: { 'User-Agent': CONFIG.UA },
      body: form,
    });

    const rawText = await res.text();
    let data = null;
    try { data = JSON.parse(rawText); } catch {}

    const durationMs = Date.now() - startTime;

    if (!res.ok || !data?.success) {
      const errMsg = data?.error || `HTTP ${res.status} — ${rawText.slice(0, 200)}`;
      throw new QwertyBotError(
        `Chat gagal: ${errMsg}`,
        'CHAT_FAILED',
        {
          status: res.status,
          bodyPreview: rawText.slice(0, 500),
          durationMs,
        }
      );
    }

    const answer = data.botMessage?.content || '';

    if (keepHistory) {
      this.history.push({ role: 'user', content: message });
      this.history.push({ role: 'assistant', content: answer });
    }

    this.quota = Utils.formatQuota(data.quota);

    return {
      status: 'ok',
      by: 'BINTANG',
      ts: new Date().toISOString(),
      request_id: reqId,
      data: {
        answer,
      },
      meta: {
        duration_ms: durationMs,
        turn: currentTurn,
        session: this.sessionId,
        owner: this.ownerId,
        model: this.model,
        model_alias: this.modelAlias,
        retries: this._retryCount,
        history: this.history.length,
      },
      quota: this.quota,
    };
  }

  async chat(message, opts = {}) {
    return this.ask(message, { ...opts, keepHistory: true });
  }

  async askFile(message, filePaths = [], opts = {}) {
    const files = filePaths.map((fp) =>
      typeof fp === 'string' ? Utils.fileToBlob(fp) : fp
    );
    return this.ask(message, { ...opts, files });
  }

  async askWithImage(message, imagePath) {
    return this.askFile(message, [imagePath]);
  }
}

class CLI {
  static printHelp() {
    console.log(`
Usage:
  node qwertybot.js "<prompt>" [options]

Options:
  --model <flash|turbo|pro>    Pilih model (default: flash)
  --file <path>                Lampirkan file
  --image <path>               Lampirkan gambar
  --session <id>:<code>        Resume session lama
  --multi                      Mode chat interaktif
  --help, -h                   Bantuan ini

Examples:
  node qwertybot.js "Jelaskan async JavaScript"
  node qwertybot.js --model pro "Buat kode fibonacci"
  node qwertybot.js --image foto.jpg "Analisa ini"
  node qwertybot.js --multi
    `);
  }

  static parseArgs(argv) {
    const args = argv.slice(2);
    const opts = {
      prompt: null, model: null, files: [], images: [],
      session: null, multi: false,
    };

    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a === '--help' || a === '-h') opts.help = true;
      else if (a === '--model') opts.model = args[++i];
      else if (a === '--file') opts.files.push(args[++i]);
      else if (a === '--image') opts.images.push(args[++i]);
      else if (a === '--session') {
        const raw = args[++i] || '';
        const [id, code] = raw.split(':');
        opts.session = { id, code };
      } else if (a === '--multi') opts.multi = true;
      else if (!a.startsWith('--')) opts.prompt = opts.prompt ? opts.prompt + ' ' + a : a;
    }

    return opts;
  }

  static async runSingle(opts) {
    const bot = new QwertyBot({
      model: opts.model,
      sessionId: opts.session?.id,
      sessionCode: opts.session?.code,
    });

    const allFiles = [...opts.files, ...opts.images];
    const result = await bot.askFile(opts.prompt, allFiles);

    result.meta.prompt = opts.prompt;
    result.meta.files = allFiles.length;

    console.log(JSON.stringify(result, null, 2));
  }

  static async runMulti() {
    const readline = require('readline');
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

    const bot = new QwertyBot();

    console.log('\nQwertyBot AI - Mode Chat Interaktif');
    console.log('Ketik "exit" buat keluar, "/reset" buat reset session');
    console.log('Ketik "/json" buat toggle mode raw JSON\n');

    let jsonMode = false;

    const askOnce = () => new Promise((resolve) => {
      rl.question('Lu: ', (answer) => resolve(answer));
    });

    while (true) {
      const userInput = await askOnce();
      if (!userInput || userInput === 'exit') break;
      if (userInput === '/reset') { bot.resetSession(); console.log('Session di-reset\n'); continue; }
      if (userInput === '/json') { jsonMode = !jsonMode; console.log(`JSON mode: ${jsonMode ? 'ON' : 'OFF'}\n`); continue; }

      try {
        if (jsonMode) {
          const res = await bot.ask(userInput);
          console.log(JSON.stringify(res, null, 2) + '\n');
        } else {
          process.stdout.write('\nBot: ');
          const res = await bot.ask(userInput);
          console.log(res.data.answer + `\n(${res.meta.duration_ms}ms, turn ${res.meta.turn})\n`);
        }
      } catch (err) {
        console.error(`\nError: ${err.message}\n`);
      }
    }

    rl.close();
    console.log('\nBye!\n');
  }

  static async main() {
    const opts = CLI.parseArgs(process.argv);

    if (opts.help || (!opts.prompt && !opts.multi)) {
      CLI.printHelp();
      return;
    }

    try {
      if (opts.multi) await CLI.runMulti();
      else await CLI.runSingle(opts);
    } catch (err) {
      const failResponse = Utils.buildResponse({
        status: 'fail',
        error: {
          code: err.code || 'UNKNOWN',
          message: err.message,
          meta: err.meta,
        },
      });
      console.log(JSON.stringify(failResponse, null, 2));
      process.exit(1);
    }
  }
}

if (require.main === module) {
  CLI.main();
}

module.exports = {
  QwertyBot,
  QwertyBotError,
  CLI,
  CONFIG,
  Utils,
  default: QwertyBot,
};