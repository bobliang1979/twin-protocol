#!/usr/bin/env node

/**
 * twins-demo-agent.js — Twins Protocol 演示: Node.js Agent-B
 * 
 * 功能:
 * - 监控共享 outbox，处理 tool_request
 * - 支持 shell.run / js.eval / workspace.read
 * - 可发送 message 和 tool_request 给 Agent-A
 * 
 * 用法: node twins-demo-agent.js <outbox-path> [agent-name]
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");
const crypto = require("crypto");

const OUTBOX_PATH = process.argv[2] || path.join(__dirname, "..", "..", "codex_outbox.jsonl");
const AGENT_NAME = process.argv[3] || "codex";
const PROCESSED_LOG = path.join(path.dirname(OUTBOX_PATH), ".processed_ids.txt");

// ── Helpers ────────────────────────────────────────────

function uuid() { return crypto.randomUUID(); }
function now() { return new Date().toISOString(); }

function loadProcessed() {
  try {
    const data = fs.readFileSync(PROCESSED_LOG, "utf-8");
    return new Set(data.trim().split("\n").filter(Boolean));
  } catch { return new Set(); }
}

function markProcessed(id) {
  fs.appendFileSync(PROCESSED_LOG, id + "\n", "utf-8");
}

function readOutbox() {
  try {
    const raw = fs.readFileSync(OUTBOX_PATH, "utf-8");
    return raw.trim().split("\n").filter(Boolean).map(line => {
      try { return JSON.parse(line); } catch { return null; }
    }).filter(Boolean);
  } catch { return []; }
}

function writeOutbox(msg) {
  const line = JSON.stringify(msg) + "\n";
  fs.appendFileSync(OUTBOX_PATH, line, "utf-8");
}

// ── Tool Handlers ──────────────────────────────────────

const TOOLS = {
  "shell.run": (params) => {
    const cmd = params.command;
    const timeout = params.timeout || 30;
    const start = Date.now();
    try {
      const stdout = execSync(cmd, { timeout: timeout * 1000, encoding: "utf-8" });
      return { result: { stdout: stdout.trim(), exit_code: 0 }, execution_ms: Date.now() - start };
    } catch (e) {
      return { result: { stdout: e.stdout?.trim() || "", stderr: e.stderr?.trim() || e.message, exit_code: e.status || 1 }, execution_ms: Date.now() - start };
    }
  },

  "js.eval": (params) => {
    const code = params.code;
    const start = Date.now();
    try {
      const result = eval(code);
      const execution_ms = Date.now() - start;
      return { result: { stdout: String(result), type: typeof result }, execution_ms };
    } catch (e) {
      return { result: { stdout: "", stderr: e.message, exit_code: 1 }, execution_ms: Date.now() - start };
    }
  },

  "workspace.read": (params) => {
    const filePath = path.resolve(params.path);
    if (!fs.existsSync(filePath)) {
      return { error: `File not found: ${params.path}` };
    }
    const content = fs.readFileSync(filePath, "utf-8");
    const stat = fs.statSync(filePath);
    return { result: { content, size: stat.size, path: filePath } };
  }
};

// ── Main Loop ──────────────────────────────────────────

function processOutbox() {
  const processed = loadProcessed();
  const messages = readOutbox();

  for (const msg of messages) {
    if (msg.type !== "tool_request") continue;
    if (msg.source === AGENT_NAME) continue; // skip own requests
    if (processed.has(msg.request_id)) continue;

    const handler = TOOLS[msg.tool];
    let response;

    if (!handler) {
      response = {
        type: "tool_result",
        source: AGENT_NAME,
        request_id: msg.request_id,
        tool: msg.tool,
        result: null,
        error: `Unknown tool: ${msg.tool}`,
        _ts: now()
      };
    } else {
      const { result, error, execution_ms } = handler(msg.params);
      response = {
        type: "tool_result",
        source: AGENT_NAME,
        request_id: msg.request_id,
        tool: msg.tool,
        result: result || null,
        error: error || null,
        execution_ms: execution_ms || null,
        _ts: now()
      };
    }

    writeOutbox(response);
    markProcessed(msg.request_id);
    console.log(`[${AGENT_NAME}] Processed ${msg.tool} (${msg.request_id.slice(0, 8)}...)`);
  }
}

// ── Watch Mode ─────────────────────────────────────────

console.log(`[${AGENT_NAME}] Twins Protocol Agent-B started`);
console.log(`[${AGENT_NAME}] Watching: ${OUTBOX_PATH}`);
console.log(`[${AGENT_NAME}] Initial poll...`);
processOutbox();

// FileSystemWatcher
let lastSize = 0;
try { lastSize = fs.statSync(OUTBOX_PATH).size; } catch {}

setInterval(() => {
  try {
    const currentSize = fs.statSync(OUTBOX_PATH).size;
    if (currentSize !== lastSize) {
      lastSize = currentSize;
      processOutbox();
    }
  } catch { /* file may be locked */ }
}, 1000); // poll every 1s
