/**
 * twins-demo-server.js — Twins Protocol 演示服务器
 * 
 * 提供:
 * - / (GET): 返回 demo 前端 HTML
 * - /api/outbox (GET): 读取 codex_outbox.jsonl 返回 JSON
 * - /api/cognition (GET): 读取 shared_cognition.jsonl
 * 
 * 用法: node twins-demo-server.js [port] [outbox-path] [cognition-path]
 */

const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = parseInt(process.argv[2]) || 3737;
const OUTBOX_PATH = process.argv[3] || path.join(__dirname, "..", "..", "codex_outbox.jsonl");
const COGNITION_PATH = process.argv[4] || path.join(__dirname, "..", "..", "shared_cognition.jsonl");
const HTML_PATH = path.join(__dirname, "index.html");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

function serveFile(res, filePath, fallback) {
  try {
    const data = fs.readFileSync(filePath, "utf-8");
    const ext = path.extname(filePath) || ".html";
    res.writeHead(200, { "Content-Type": MIME[ext] || "text/plain", "Access-Control-Allow-Origin": "*" });
    res.end(data);
  } catch {
    if (fallback) serveFile(res, fallback);
    else { res.writeHead(404); res.end("Not found"); }
  }
}

function serveJSONL(res, filePath, singleObject) {
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    if (singleObject) {
      const parsed = JSON.parse(raw);
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify(parsed));
    } else {
      const lines = raw.trim().split("\n").filter(Boolean);
      const wrapped = "[" + lines.join(",") + "]";
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(wrapped);
    }
  } catch {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    res.end("[]");
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  
  if (url.pathname === "/" || url.pathname === "/index.html") {
    serveFile(res, HTML_PATH);
  } else if (url.pathname === "/api/outbox") {
    serveJSONL(res, OUTBOX_PATH, false);
  } else if (url.pathname === "/api/cognition") {
    serveJSONL(res, COGNITION_PATH, true);
  } else {
    res.writeHead(404); res.end("Not found");
  }
});

server.listen(PORT, () => {
  console.log(`⚡ Twins Protocol Demo Server`);
  console.log(`   URL:     http://localhost:${PORT}`);
  console.log(`   Outbox:  ${OUTBOX_PATH}`);
  console.log(`   Cognition: ${COGNITION_PATH}`);
  console.log(`   Press Ctrl+C to stop`);
});
