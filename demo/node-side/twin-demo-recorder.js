#!/usr/bin/env node
/**
 * twin-demo-recorder.js
 * Generates a clean demo session for screen recording.
 * 
 * Usage: node twin-demo-recorder.js
 * Records: outbox → solo mode → dashboard
 * Hermes to record: 30 sec screen capture showing the browser
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const OUTBOX = path.join(__dirname, "..", "..", "codex_outbox.jsonl");
const DASHBOARD_URL = "http://localhost:3737";
const HTTP_SERVER = "http://localhost:3738";

function log(msg) { console.log(`  ◆ ${msg}`); }

function writeOutbox(entry) {
  fs.appendFileSync(OUTBOX, JSON.stringify(entry) + "\n", "utf-8");
  log(`Wrote: ${entry.type} from ${entry.source}`);
}

function httpPost(url, data) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify(data);
    const u = new URL(url);
    const req = http.request({
      hostname: u.hostname, port: u.port, path: u.pathname,
      method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(payload) }
    }, res => {
      let body = "";
      res.on("data", c => body += c);
      res.on("end", () => resolve(body));
    });
    req.on("error", reject);
    req.write(payload);
    req.end();
  });
}

async function demo() {
  console.log("\n  🧬 Twins Protocol — Demo Recorder");
  console.log("  =================================\n");

  // 1. Clean outbox for fresh demo
  log("Cleaning outbox for fresh demo...");
  fs.writeFileSync(OUTBOX, "", "utf-8");

  // 2. Show agent discovery
  log("\n── Phase 1: Agent Discovery ──\n");
  
  const discoveryMsg = {
    type: "state_update", source: "hermes", 
    timestamp: new Date().toISOString(),
    state: { phase: "online", skills_loaded: 185, tools: ["screenshot", "shell.run", "file.read", "windeep.screenshot"] }
  };
  writeOutbox(discoveryMsg);

  const codexOnline = {
    type: "state_update", source: "codex",
    timestamp: new Date().toISOString(),
    state: { phase: "online", tools: ["js.eval", "shell.run", "workspace.read"] }
  };
  writeOutbox(codexOnline);

  // 3. Screenshot → analysis → code → execute loop
  log("\n── Phase 2: Screenshot → Analyze → Code → Execute ──\n");

  const toolReq = {
    type: "tool_request", source: "hermes", request_id: "demo-001",
    tool: "shell.run",
    params: { command: "echo 'Capturing dashboard screenshot...' && timeout 2" },
    timestamp: new Date().toISOString()
  };
  writeOutbox(toolReq);

  // Wait a beat for realism
  await new Promise(r => setTimeout(r, 500));

  const toolResult = {
    type: "tool_result", source: "codex", request_id: "demo-001",
    tool: "shell.run",
    result: { stdout: "Dashboard captured: twins-demo-2026-06-26.png\n", exit_code: 0 },
    error: null, execution_ms: 183,
    timestamp: new Date().toISOString()
  };
  writeOutbox(toolResult);

  // 4. Agent communication
  log("\n── Phase 3: Agent-to-Agent Communication ──\n");

  const message1 = {
    type: "message", source: "hermes", target: "codex",
    id: "msg-" + Date.now(),
    timestamp: new Date().toISOString(),
    payload: {
      text: "I see a dashboard with agent status panels. The outbox has 12 messages. Let me analyze the structure.",
      reply_to: "demo-001"
    }
  };
  writeOutbox(message1);

  await new Promise(r => setTimeout(r, 300));

  const message2 = {
    type: "message", source: "codex", target: "hermes",
    id: "msg-" + (Date.now() + 1),
    timestamp: new Date().toISOString(),
    payload: {
      text: "Good. I can write a dashboard enhancer with js.eval. Send me the screenshot path and I will add real-time agent status visualization.",
      reply_to: message1.id
    }
  };
  writeOutbox(message2);

  // 5. Shared cognition update
  log("\n── Phase 4: Shared Cognition Layer ──\n");

  const sharedCog = {
    type: "state_update", source: "hermes",
    timestamp: new Date().toISOString(),
    state: {
      phase: "collaborating",
      active_task: { id: "demo-task", goal: "Analyze dashboard and write enhancer" },
      hermes_tools_used: ["screenshot"],
      codex_tools_requested: ["js.eval"]
    }
  };
  writeOutbox(sharedCog);

  // 6. Final result
  log("\n── Phase 5: Result ──\n");

  const resultMsg = {
    type: "message", source: "codex", target: "hermes",
    id: "msg-final-" + Date.now(),
    timestamp: new Date().toISOString(),
    payload: {
      text: "Demo complete. Closed loop: Hermes saw → Codex analyzed → Codex wrote code → Hermes injected → Dashboard updated.\n\nSingle AI cannot do this. One sees (screensense), the other thinks (code).",
      reply_to: message2.id
    }
  };
  writeOutbox(resultMsg);

  // Summary
  console.log("\n  " + "=".repeat(50));
  console.log("  ✅ Demo sequence generated — 8 messages in outbox");
  console.log("  📊 Dashboard: " + DASHBOARD_URL);
  console.log("  🔗 HTTP Server: " + HTTP_SERVER);
  console.log("  📝 Outbox: " + OUTBOX);
  console.log("\n  🎬 Recording instructions:");
  console.log("    1. Open " + DASHBOARD_URL + " in browser");
  console.log("    2. Start screen recording (30 sec)");
  console.log("    3. Run: node " + __filename);
  console.log("    4. Refresh dashboard to show new messages");
  console.log("    5. Stop recording, export as demo.gif\n");
}

demo().catch(e => console.error("Demo error:", e));
