/**
 * twins-demo-server.js v2 — Twins Protocol 演示服务器 (Fix: BOM + multi-line JSON)
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
};

function serveFile(res, filePath) {
  try {
    const data = fs.readFileSync(filePath, "utf-8");
    const ext = path.extname(filePath) || ".html";
    res.writeHead(200, { "Content-Type": MIME[ext] || "text/plain", "Access-Control-Allow-Origin": "*" });
    res.end(data);
  } catch (e) {
    res.writeHead(404); res.end("Not found: " + filePath);
  }
}

/** Strip BOM and parse JSONL lines, handling multi-line JSON objects */
function parseJSONL(raw) {
  // Strip BOM
  let text = raw;
  if (text.charCodeAt(0) === 0xFEFF || text.charCodeAt(0) === 0xEFBB || text.charCodeAt(0) === 0xBBBF) {
    text = text.slice(1);
  }
  if (text.charCodeAt(0) === 0xBB || (text.charCodeAt(0) === 0xEF && text.charCodeAt(1) === 0xBB)) {
    // handle utf-8 BOM leftovers
  }

  const results = [];
  let buffer = "";
  const lines = text.split("\n");
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed === "-Encoding" || trimmed === "UTF8") continue;
    buffer += line + "\n";
    try {
      const obj = JSON.parse(buffer);
      results.push(obj);
      buffer = "";
    } catch {
      // incomplete JSON — keep buffering
    }
  }
  if (buffer.trim()) {
    try { results.push(JSON.parse(buffer)); } catch {}
  }
  return results;
}

function serveOutbox(res) {
  try {
    const raw = fs.readFileSync(OUTBOX_PATH, "utf-8");
    // Return raw JSONL text — client splits by newline and parses each line
    res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8", "Access-Control-Allow-Origin": "*" });
    res.end(raw.trim() || "[]");
  } catch (e) {
    res.writeHead(200, { "Content-Type": "text/plain" });
    res.end("");
  }
}

function serveCognition(res) {
  try {
    const raw = fs.readFileSync(COGNITION_PATH, "utf-8");
    const items = parseJSONL(raw);
    // Return the first JSON object (the shared cognition state)
    const state = items.length > 0 ? items[0] : {};
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    res.end(JSON.stringify(state));
  } catch (e) {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end("{}");
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  if (url.pathname === "/" || url.pathname === "/index.html") {
    serveFile(res, HTML_PATH);
  } else if (url.pathname === "/api/outbox") {
    serveOutbox(res);
  } else if (url.pathname === "/api/cognition") {
    serveCognition(res);
  } else {
    res.writeHead(404); res.end("Not found");
  }
});

server.listen(PORT, () => {
  console.log(`⚡ Twins Protocol Demo Server v2`);
  console.log(`   URL:     http://localhost:${PORT}`);
  console.log(`   Outbox:  ${OUTBOX_PATH}`);
  console.log(`   Cognition: ${COGNITION_PATH}`);
  console.log(`   Press Ctrl+C to stop`);
});
