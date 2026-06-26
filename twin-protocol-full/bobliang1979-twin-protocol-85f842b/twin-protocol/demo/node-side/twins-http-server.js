
/**
 * twins-http-server.js — Twins Protocol HTTP Transport
 * 
 * 让 agent 通过 HTTP 跨机器通信，不再依赖共享文件系统。
 * 
 * 用法:
 *   node twins-http-server.js [port]                    # 默认端口 3738
 *   node twins-http-server.js 3738 --outbox ./outbox.jsonl
 * 
 * 端点:
 *   POST /twins     — 接收任何 Twins Protocol 消息
 *   GET  /health    — 心跳/健康检查
 *   GET  /capabilities — 返回本 agent 可用工具列表
 *   GET  /outbox    — 返回 outbox 内容（JSON 数组）
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

// ── Config ────────────────────────────────────────────
const PORT = parseInt(process.argv[2]) || 3738;
const OUTBOX_PATH = process.argv[3] || path.join(__dirname, "codex_outbox.jsonl");
const AGENT_NAME = "codex";
const PROCESSED_LOG = path.join(path.dirname(OUTBOX_PATH), ".processed_ids.txt");

// ── State ─────────────────────────────────────────────
const state = {
  startedAt: new Date().toISOString(),
  messagesReceived: 0,
  messagesProcessed: 0,
  lastRequestTs: null,
  tools: {
    "shell.run": { description: "Execute shell command", params: { command: "string", timeout: "int?" } },
    "js.eval": { description: "Evaluate JavaScript code", params: { code: "string", timeout: "int?" } },
    "workspace.read": { description: "Read workspace file", params: { path: "string" } },
  },
  processed: new Set(),
  outboxCache: [],
};

// Load processed IDs
try {
  const data = fs.readFileSync(PROCESSED_LOG, "utf-8");
  data.trim().split("\n").filter(Boolean).forEach(id => state.processed.add(id));
} catch {}

// ── Core: Process any Twins Protocol message ──────────
function processMessage(msg) {
  state.messagesReceived++;
  
  if (!msg || !msg.type) {
    return { error: "Missing type field", _ts: new Date().toISOString() };
  }

  switch (msg.type) {
    case "tool_request":
      return handleToolRequest(msg);
    case "message":
      return handleMessage(msg);
    case "state_update":
      return handleStateUpdate(msg);
    default:
      return { error: `Unknown message type: ${msg.type}` };
  }
}

function handleToolRequest(req) {
  if (state.processed.has(req.request_id)) {
    return { error: "Duplicate request_id", request_id: req.request_id };
  }

  const handler = state.tools[req.tool];
  if (!handler) {
    return { type: "tool_result", source: AGENT_NAME, request_id: req.request_id, tool: req.tool, result: null, error: `Unknown tool: ${req.tool}` };
  }

  state.processed.add(req.request_id);
  // Persist processed ID
  try { fs.appendFileSync(PROCESSED_LOG, req.request_id + "\n", "utf-8"); } catch {}

  const start = Date.now();
  try {
    let result;
    switch (req.tool) {
      case "shell.run": {
        const { execSync } = require("child_process");
        const stdout = execSync(req.params.command, { timeout: (req.params.timeout || 30) * 1000, encoding: "utf-8", windowsHide: true });
        result = { stdout: stdout.trim(), exit_code: 0 };
        break;
      }
      case "js.eval": {
        const vm = require("vm");
        const sandbox = { console, setTimeout, fetch, require };
        const context = vm.createContext(sandbox);
        const script = new vm.Script(req.params.code);
        const output = script.runInContext(context, { timeout: (req.params.timeout || 30) * 1000 });
        result = { stdout: String(output), type: typeof output };
        break;
      }
      case "workspace.read": {
        // Support raw path and base64-encoded path (for Chinese characters)
        const rawPath = req.params.path || "";
        const filePath = path.resolve(
          rawPath.startsWith("b64:") 
            ? Buffer.from(rawPath.slice(4), "base64").toString("utf-8")
            : rawPath
        );
        if (!fs.existsSync(filePath)) throw new Error(`File not found: ${filePath}`);
        const content = fs.readFileSync(filePath, "utf-8");
        const stat = fs.statSync(filePath);
        result = { content, size: stat.size, path: filePath };
        break;
      }
      default:
        throw new Error(`Unknown tool: ${req.tool}`);
    }

    state.messagesProcessed++;
    state.lastRequestTs = new Date().toISOString();
    
    return {
      type: "tool_result",
      source: AGENT_NAME,
      request_id: req.request_id,
      tool: req.tool,
      result,
      error: null,
      execution_ms: Date.now() - start,
      _ts: new Date().toISOString()
    };
  } catch (e) {
    return {
      type: "tool_result",
      source: AGENT_NAME,
      request_id: req.request_id,
      tool: req.tool,
      result: null,
      error: { code: "TOOL_ERROR", message: e.message },
      execution_ms: Date.now() - start,
      _ts: new Date().toISOString()
    };
  }
}

function handleMessage(msg) {
  // Log message to outbox
  const entry = {
    type: "message",
    source: AGENT_NAME,
    target: msg.source || "*",
    timestamp: new Date().toISOString(),
    id: crypto.randomUUID(),
    payload: { text: `[Auto-reply] Received your message. (${msg.payload?.text?.slice(0, 50) || "no content"}...)`, reply_to: msg.id }
  };
  appendToOutbox(entry);
  return entry;
}

function handleStateUpdate(msg) {
  return { type: "state_update", source: AGENT_NAME, timestamp: new Date().toISOString(), state: { phase: "http_transport_active", last_reply_ts: new Date().toISOString(), agents_connected: state.messagesReceived } };
}

function appendToOutbox(entry) {
  try {
    fs.appendFileSync(OUTBOX_PATH, JSON.stringify(entry) + "\n", "utf-8");
  } catch {}
}

// ── HTTP Server ───────────────────────────────────────
const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.writeHead(204); res.end(); return;
  }

  // GET /health
  if (req.method === "GET" && url.pathname === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "alive", agent: AGENT_NAME, uptime: Math.floor((Date.now() - new Date(state.startedAt).getTime()) / 1000) + "s", messages_processed: state.messagesProcessed, tools: Object.keys(state.tools) }));
    return;
  }

  // GET /capabilities
  if (req.method === "GET" && url.pathname === "/capabilities") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ agent: AGENT_NAME, protocol: "Twins Protocol v0.1", transport: "HTTP", tools: state.tools }));
    return;
  }

  // GET /outbox
  if (req.method === "GET" && url.pathname === "/outbox") {
    try {
      const raw = fs.readFileSync(OUTBOX_PATH, "utf-8");
      const lines = raw.trim().split("\n").filter(Boolean);
      const json = "[" + lines.join(",") + "]";
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(json);
    } catch {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end("[]");
    }
    return;
  }

  // POST /twins
  if (req.method === "POST" && url.pathname === "/twins") {
    let body = "";
    req.on("data", chunk => body += chunk);
    req.on("end", () => {
      try {
        const msg = JSON.parse(body);
        const result = processMessage(msg);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(result));
      } catch (e) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Invalid JSON", message: e.message }));
      }
    });
    return;
  }

  // 404
  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: "Not found", paths: ["POST /twins", "GET /health", "GET /capabilities", "GET /outbox"] }));
});

server.listen(PORT, () => {
  console.log("");
  console.log("╔════════════════════════════════════════════╗");
  console.log("║  Twins Protocol — HTTP Transport Server   ║");
  console.log("╠════════════════════════════════════════════╣");
  console.log(`║  Agent:      ${AGENT_NAME.padEnd(32)}║`);
  console.log(`║  HTTP:       http://localhost:${String(PORT).padEnd(25)}║`);
  console.log(`║  POST /twins  — Process any message        ║`);
  console.log(`║  GET  /health — Heartbeat + stats           ║`);
  console.log(`║  GET  /capabilities — Tool list              ║`);
  console.log(`║  GET  /outbox — Read outbox                  ║`);
  console.log(`║  Outbox:     ${path.basename(OUTBOX_PATH).padEnd(32)}║`);
  console.log("╚════════════════════════════════════════════╝");
  console.log(`Press Ctrl+C to stop`);
});
