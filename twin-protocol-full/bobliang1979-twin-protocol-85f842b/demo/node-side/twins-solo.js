/**
 * twins-solo.js — Twins Protocol Solo Mode
 * Single developer can experience two AI agents collaborating
 * Usage: node twins-solo.js
 * Open: http://localhost:3737
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const PORT = 3737;
const OUTBOX = path.join(__dirname, "solo_outbox.jsonl");
const COGNITION = path.join(__dirname, "solo_cognition.jsonl");

const AGENTS = {
  alice: { name: "Alice (Python)", tools: ["shell.run", "file.read", "file.write", "screenshot"] },
  bob: { name: "Bob (Node.js)", tools: ["shell.run", "js.eval", "workspace.read"] }
};

let scenarioIdx = 0;
let isPlaying = false;

function uuid() { return crypto.randomUUID(); }
function now() { return new Date().toISOString(); }

const SCENES = [
  { from: "alice", type: "message", text: "Hey Bob, ready to build a web app together?" },
  { from: "bob", type: "message", text: "Ready! I'll handle the Node.js backend." },
  { from: "alice", type: "tool_request", tool: "shell.run", params: { command: "echo 'Starting...'" } },
  { from: "bob", type: "tool_result", tool: "shell.run", result: { stdout: "Starting...", exit_code: 0 } },
  { from: "bob", type: "tool_request", tool: "js.eval", params: { code: "2 + 2" } },
  { from: "alice", type: "tool_result", tool: "js.eval", result: { stdout: "4", type: "number" } },
  { from: "alice", type: "message", text: "API contract: POST /api/data -> JSON. Agreed?" },
  { from: "bob", type: "message", text: "Agreed. Building endpoint now." },
  { from: "alice", type: "state_update", state: { phase: "building", task: "data module" } },
  { from: "bob", type: "state_update", state: { phase: "building", task: "API endpoint" } },
  { from: "bob", type: "message", text: "Endpoint ready at http://localhost:8080/api" },
  { from: "alice", type: "message", text: "Deploying! Two agents, one protocol, zero friction." },
];

function writeJSONL(file, obj) {
  fs.appendFileSync(file, JSON.stringify(obj) + "\n", "utf-8");
}

function writeCognition(state) {
  fs.writeFileSync(COGNITION, JSON.stringify(state), "utf-8");
}

// Init
writeCognition({ session_id: "solo-demo", goal: "Two AI agents building a web app", phase: "idle", progress: "0%" });

function playNext() {
  if (isPlaying || scenarioIdx >= SCENES.length) return;
  isPlaying = true;
  const s = SCENES[scenarioIdx++];
  setTimeout(() => {
    const msg = { type: s.type, source: s.from, timestamp: now(), id: uuid() };
    if (s.type === "message") { msg.target = s.from === "alice" ? "bob" : "alice"; msg.payload = { text: s.text }; }
    else if (s.type === "tool_request") { msg.request_id = uuid(); msg.tool = s.tool; msg.params = s.params; }
    else if (s.type === "tool_result") { msg.request_id = uuid(); msg.tool = s.tool; msg.result = s.result; msg.error = null; msg.execution_ms = 10 + Math.floor(Math.random() * 90); msg._ts = now(); }
    else if (s.type === "state_update") { msg.state = s.state; }
    writeJSONL(OUTBOX, msg);
    writeCognition({ session_id: "solo-demo", goal: "Two AI agents building a web app", phase: "running", progress: Math.round(scenarioIdx / SCENES.length * 100) + "%" });
    isPlaying = false;
  }, (s.wait || 1) * 1000);
}

const server = http.createServer((req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  const url = new URL(req.url, "http://localhost:" + PORT);
  if (url.pathname === "/" || url.pathname === "/index.html") {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(getHTML()); return;
  }
  if (url.pathname === "/api/outbox") {
    try { const d = fs.readFileSync(OUTBOX, "utf-8").trim(); res.writeHead(200, { "Content-Type": "application/json" }); res.end("[" + d.split("\n").filter(Boolean).join(",") + "]"); }
    catch { res.writeHead(200, { "Content-Type": "application/json" }); res.end("[]"); }
    return;
  }
  if (url.pathname === "/api/cognition") {
    try { res.writeHead(200, { "Content-Type": "application/json" }); res.end(fs.readFileSync(COGNITION, "utf-8")); }
    catch { res.writeHead(200, { "Content-Type": "application/json" }); res.end("{}"); }
    return;
  }
  if (url.pathname === "/api/start") {
    scenarioIdx = 0; try { fs.writeFileSync(OUTBOX, "", "utf-8"); } catch {}
    writeCognition({ session_id: "solo-demo", goal: "Two AI agents building a web app", phase: "starting", progress: "0%" });
    const iv = setInterval(() => { playNext(); if (scenarioIdx >= SCENES.length) clearInterval(iv); }, 1500);
    playNext();
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "started", scenes: SCENES.length }));
    return;
  }
  res.writeHead(404); res.end();
});

server.listen(PORT, () => {
  console.log("");
  console.log("  Twins Protocol — Solo Mode");
  console.log("  Dashboard: http://localhost:" + PORT);
  console.log("  Two AI agents collaborating through a single file.");
  console.log("");
});

function getHTML() {
  return '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Twins Solo</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:monospace;background:#0d1117;color:#e6edf3;min-height:100vh}.h{border-bottom:1px solid #30363d;padding:16px 24px;display:flex;align-items:center;gap:16px}.h h1{font-size:18px}.b{background:#238636;color:#fff;padding:2px 10px;border-radius:12px;font-size:12px}.s{display:flex;gap:24px;padding:8px 24px;background:#161b22;font-size:12px;color:#8b949e}.d{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:#3fb950;animation:p 2s infinite}@keyframes p{0%,100%{opacity:1}50%{opacity:.4}}.c{display:flex;height:calc(100vh-80px)}.col{flex:1;display:flex;flex-direction:column;border-right:1px solid #30363d;overflow:hidden}.col:last-child{border-right:none}.ch{padding:12px 16px;font-weight:600;font-size:14px;border-bottom:1px solid #30363d;display:flex;align-items:center;gap:8px}.ca .ch{background:#1c2333}.cb .ch{background:#1c2a1c}.l{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:6px}.e{padding:8px 12px;border-radius:8px;font-size:13px;line-height:1.5;border:1px solid transparent;animation:f .3s}@keyframes f{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}.e.message{background:#161b22;border-color:#30363d}.e.tool_request{background:#1a2332;border-color:#1f6feb}.e.tool_result{background:#1a2e1a;border-color:#238636}.e.state_update{background:#2a1a2e;border-color:#8957e5}.m{font-size:11px;color:#8b949e;margin-bottom:4px}.t{display:inline-block;padding:0 6px;border-radius:4px;font-size:10px;font-weight:600;margin-right:6px}.t.tool_request{background:#1f6feb33;color:#58a6ff}.t.tool_result{background:#23863633;color:#3fb950}.t.message{background:#30363d;color:#e6edf3}.t.state_update{background:#8957e533;color:#a371f7}.bdy{white-space:pre-wrap}.btn{background:#238636;color:#fff;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px;margin-left:auto}.btn:hover{background:#2ea043}.btn:disabled{opacity:.5}</style></head><body><div class="h"><h1>Twins Protocol</h1><span class="b">Solo</span><span style="font-size:12px;color:#8b949e;margin-left:auto">Two AIs through a single file</span><button class="btn" id="sb" onclick="start()">Start</button></div><div class="s"><span><span class="d"></span> Alice (Python)</span><span><span class="d"></span> Bob (Node.js)</span><span id="mc">0</span><span id="pg">0%</span></div><div class="c"><div class="col ca"><div class="ch">Alice Python</div><div class="l" id="la"></div></div><div class="col cb"><div class="ch">Bob Node.js</div><div class="l" id="lb"></div></div></div><script>async function j(u){const r=await fetch(u);return r.json()}async function start(){document.getElementById("sb").disabled=true;document.getElementById("sb").textContent="Running...";await fetch("/api/start")}async function u(){const m=await j("/api/outbox"),c=await j("/api/cognition");document.getElementById("mc").textContent=m.length+" msgs";document.getElementById("pg").textContent=c.progress||"0%";["alice","bob"].forEach(a=>{const l=document.getElementById(a==="alice"?"la":"lb"),am=m.filter(x=>x.source===a);l.innerHTML=am.slice(-15).reverse().map(x=>{const t=x.type||"message";let b="";if(x.type==="message")b=x.payload?.text||"";else if(x.type==="tool_request")b="Call: "+x.tool;else if(x.type==="tool_result")b="Done: "+(x.result?.stdout||"").slice(0,50);else if(x.type==="state_update")b=x.state?.phase||"";return\'<div class="e \'+t+\'"><div class="m"><span class="t \'+t+\'">\'+t+"</span></div><div class=\"bdy\">"+b+"</div></div>"}).join("")})}setInterval(u,1500);u()</script></body></html>';
}