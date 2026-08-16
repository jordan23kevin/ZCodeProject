// PETDESK 零依赖静态服务器 + 视觉 API 代理 + Lovart 生图桥 — 支持 --host / --port 参数转发
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const args = process.argv.slice(2);
function argVal(name, def) {
  const i = args.findIndex(a => a === name || a === name.replace('--', '-'));
  if (i > -1 && args[i + 1]) return args[i + 1];
  const eq = args.find(a => a.startsWith(name + '='));
  return eq ? eq.split('=')[1] : def;
}
const port = Number(argVal('--port', process.env.PORT || 7100));
const host = argVal('--host', process.env.HOST || '127.0.0.1');

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.json': 'application/json' };
const APP_VER = '2.18';

function readBody(req) {
  return new Promise((res, rej) => {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => res(Buffer.concat(chunks)));
    req.on('error', rej);
  });
}

// 运行日志：前端步骤 + 代理转发记录，写入 petdesk.log（超 512KB 自动截断重写）
const LOG_FILE = path.join(__dirname, 'petdesk.log');
function appLog(line) {
  try {
    const stat = fs.existsSync(LOG_FILE) ? fs.statSync(LOG_FILE) : null;
    if (stat && stat.size > 512 * 1024) fs.writeFileSync(LOG_FILE, '');
    fs.appendFileSync(LOG_FILE, `[${new Date().toLocaleString('zh-CN', { hour12: false })}] ${line}\n`);
  } catch (e) {}
}
async function handleClientLog(req, res) {
  const raw = await readBody(req);
  try { appLog('页面 | ' + JSON.parse(raw.toString('utf8')).msg); } catch (e) {}
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end('{"ok":true}');
}

// 视觉 API 代理：浏览器 → 本服务器 → 视觉模型端点（规避浏览器 CORS）
// 支持两种协议：Anthropic（Kimi 编程网关 sk-kimi-）与 OpenAI 兼容（开放平台/豆包/通义）
async function handleVisionProxy(req, res) {
  try {
    const raw = await readBody(req);
    if (raw.length > 8 * 1024 * 1024) { res.writeHead(413); return res.end('{"error":"payload too large"}'); }
    const { endpoint, key, proto, payload } = JSON.parse(raw.toString('utf8'));
    if (!endpoint || !/^https:\/\//.test(endpoint)) { res.writeHead(400); return res.end('{"error":"invalid endpoint"}'); }
    if (!key) { res.writeHead(400); return res.end('{"error":"missing api key"}'); }
    const isAnt = proto !== 'openai';
    const url = endpoint.replace(/\/+$/, '') + (isAnt ? '/v1/messages' : '/chat/completions');
    const t0 = Date.now();
    appLog(`代理 | ${isAnt ? 'anthropic' : 'openai'} → ${url}`);
    const headers = isAnt
      ? { 'Content-Type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01' }
      : { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key };
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 200000);
    const upstream = await fetch(url, { method: 'POST', headers, body: JSON.stringify(payload), signal: ctrl.signal });
    clearTimeout(timer);
    const text = await upstream.text();
    appLog(`代理 | 上游 ${upstream.status} | ${Date.now() - t0}ms | ${upstream.ok ? '成功' : text.slice(0, 150)}`);
    res.writeHead(upstream.status, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(text);
  } catch (e) {
    appLog('代理 | 异常：' + String(e && e.message || e));
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: String(e && e.message || e) }));
  }
}

// 预置配置（petdesk.config.json，可选）：首次打开页面时自动填充 API 设置
function handleConfig(res) {
  fs.readFile(path.join(__dirname, 'petdesk.config.json'), (err, data) => {
    let cfg = {};
    if (!err) { try { cfg = JSON.parse(data.toString('utf8')); } catch (e) {} }
    cfg.ver = APP_VER;
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(cfg));
  });
}

// ── Lovart 生图桥 ─────────────────────────────────────────────
// 调用链：lovart_gen.py → lovart-official/skills/lovart-skill/agent_skill.py → Lovart 官方 API
// Python 路径与 lovart_bridge.bat 保持一致（受管 Python shim 已坏，不能用裸 python）
const LOVART_PY = 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe';
const LOVART_SCRIPT = path.join(__dirname, 'lovart_gen.py');
const LOVART_IN = path.join(__dirname, '_lovart_in');
const LOVART_OUT = path.join(__dirname, 'lovart_out');
let lovartRunning = 0;        // 当前并发生图任务数
const LOVART_MAX_PAR = 4;     // 最大并发：A/B 中英四通道可同时出图
const lovartKeysInUse = new Set(); // 进行中的任务占用的 key 下标，保证并发各用不同 key
const LOVART_KEYS_FILE = 'E:/Claude code/lovart-official/keys.json';

function pickFreeKeyIdx() {
  try {
    const data = JSON.parse(fs.readFileSync(LOVART_KEYS_FILE, 'utf8'));
    const free = [];
    data.keys.forEach((k, i) => {
      const disabled = k.length >= 3 && k[2] && k[2].disabled;
      if (!disabled && !lovartKeysInUse.has(i)) free.push(i);
    });
    if (!free.length) return -1;
    return free[Math.floor(Math.random() * free.length)];
  } catch (e) { return -1; }
}

async function handleLovartGenerate(req, res) {
  if (lovartRunning >= LOVART_MAX_PAR) {
    res.writeHead(409, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ error: `已有 ${LOVART_MAX_PAR} 个 Lovart 生图任务进行中，请等待完成` }));
  }
  let workDir = null;
  let keyIdx = -1;
  const finish = () => { lovartRunning--; if (keyIdx >= 0) lovartKeysInUse.delete(keyIdx); };
  try {
    const raw = await readBody(req);
    if (raw.length > 40 * 1024 * 1024) { res.writeHead(413); return res.end('{"error":"payload too large"}'); }
    const { prompt, images } = JSON.parse(raw.toString('utf8'));
    if (!prompt || !String(prompt).trim()) { res.writeHead(400); return res.end('{"error":"missing prompt"}'); }
    if (!Array.isArray(images) || !images.length) { res.writeHead(400); return res.end('{"error":"missing images"}'); }
    if (!fs.existsSync(LOVART_PY)) { res.writeHead(500); return res.end(JSON.stringify({ error: '未找到 Python：' + LOVART_PY })); }

    lovartRunning++;
    keyIdx = pickFreeKeyIdx();
    if (keyIdx >= 0) lovartKeysInUse.add(keyIdx);
    const ts = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14) + '_' + Math.random().toString(36).slice(2, 6);
    workDir = path.join(LOVART_IN, ts);
    fs.mkdirSync(workDir, { recursive: true });
    fs.mkdirSync(LOVART_OUT, { recursive: true });

    // 保存提示词与参考图（dataURL → 文件）
    const promptFile = path.join(workDir, 'prompt.txt');
    fs.writeFileSync(promptFile, String(prompt), 'utf8');
    const imgArgs = [];
    images.forEach((img, i) => {
      const m = /^data:image\/(png|jpe?g|webp);base64,(.+)$/s.exec(String(img.data || ''));
      if (!m) return;
      const ext = m[1] === 'jpeg' ? 'jpg' : m[1];
      const fp = path.join(workDir, `ref${i + 1}.${ext}`);
      fs.writeFileSync(fp, Buffer.from(m[2], 'base64'));
      imgArgs.push('--image', fp);
    });
    if (!imgArgs.length) {
      finish();
      res.writeHead(400); return res.end('{"error":"图片数据无效（需 dataURL base64）"}');
    }

    const outFile = path.join(LOVART_OUT, `main_${ts}.png`);
    appLog(`lovart | 开始生图 | 参考图=${imgArgs.length / 2} 提示词=${String(prompt).length}字 key=${keyIdx >= 0 ? '#' + (keyIdx + 1) : '随机'}`);
    const t0 = Date.now();

    const result = await new Promise((resolve) => {
      const env = { ...process.env, PYTHONPATH: 'E:/python_packages', PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' };
      const proc = spawn(LOVART_PY, [LOVART_SCRIPT, '--prompt-file', promptFile, ...imgArgs, '--out', outFile, ...(keyIdx >= 0 ? ['--key-idx', String(keyIdx)] : [])], { env });
      let buf = '';
      let lastJsonLine = '';
      const onData = d => {
        buf += d.toString('utf8');
        const lines = buf.split('\n');
        buf = lines.pop();
        lines.forEach(l => {
          const t = l.trim();
          if (t.startsWith('[petdesk]')) appLog('lovart | ' + t);
          else if (t.startsWith('{') && t.includes('"ok"')) lastJsonLine = t;
        });
      };
      proc.stdout.on('data', onData);
      proc.stderr.on('data', onData);
      // 15 分钟兜底超时
      const killer = setTimeout(() => { try { proc.kill(); } catch (e) {} }, 15 * 60 * 1000);
      proc.on('close', code => { clearTimeout(killer); resolve({ code, tail: lastJsonLine || buf }); });
      proc.on('error', e => { clearTimeout(killer); resolve({ code: -1, tail: '', err: String(e) }); });
    });

    finish();
    appLog(`lovart | 进程退出 code=${result.code} | ${Date.now() - t0}ms`);

    // 解析脚本最后一行 JSON
    let finalJson = null;
    try {
      const m = /\{[^{}]*"ok"[^{}]*\}\s*$/.exec(result.tail || '');
      if (m) finalJson = JSON.parse(m[0]);
    } catch (e) {}

    if (finalJson && finalJson.ok && fs.existsSync(outFile)) {
      appLog(`lovart | 成功 ✓ ${finalJson.image} tid=${finalJson.tid || ''}`);
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      return res.end(JSON.stringify({ ok: true, url: '/lovart_out/' + finalJson.image + '?t=' + ts, tid: finalJson.tid }));
    }
    const errMsg = (finalJson && finalJson.error) || result.err || `生图脚本异常退出(code=${result.code})`;
    appLog('lovart | 失败：' + errMsg);
    res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ error: errMsg }));
  } catch (e) {
    finish();
    appLog('lovart | 异常：' + String(e && e.message || e));
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: String(e && e.message || e) }));
  }
}

http.createServer((req, res) => {
  if (req.method === 'POST' && req.url.split('?')[0] === '/api/vision') return handleVisionProxy(req, res);
  if (req.method === 'POST' && req.url.split('?')[0] === '/api/lovart/generate') return handleLovartGenerate(req, res);
  if (req.method === 'POST' && req.url.split('?')[0] === '/api/log') return handleClientLog(req, res);
  if (req.method === 'GET' && req.url.split('?')[0] === '/api/config') return handleConfig(res);
  if (req.method === 'GET' && req.url.split('?')[0] === '/api/ping') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ ok: true, ver: APP_VER }));
  }
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') p = '/index.html';
  const file = path.join(__dirname, p);
  if (!file.startsWith(__dirname)) { res.writeHead(403); return res.end(); }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); return res.end('Not Found'); }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    res.end(data);
  });
}).listen(port, host, () => console.log(`PETDESK dev server → http://${host}:${port}/`));
