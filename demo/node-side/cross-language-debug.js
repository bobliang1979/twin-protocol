const crypto = require("crypto");
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const TEST_DIR = path.join(__dirname, ".cross-test");
if (!fs.existsSync(TEST_DIR)) fs.mkdirSync(TEST_DIR, { recursive: true });

// Python's canonicalize algorithm implemented in Node
function pythonCanonicalize(msg, signer) {
  function _hash(data) { return crypto.createHash("sha256").update(data).digest(); }
  
  const payload = (msg.payload !== undefined && msg.payload !== null) ? msg.payload : {};
  const signable = {
    type: msg.type || "message",
    source: signer,
    timestamp: msg.timestamp || "",
    id: msg.id || "",
  };
  
  const hasPayload = typeof payload === "object" && Object.keys(payload).length > 0;
  if (hasPayload) {
    const payloadJson = JSON.stringify(payload, Object.keys(payload).sort());
    signable.payload_hash = _hash(Buffer.from(payloadJson, "utf-8")).toString("base64");
  }
  
  if (msg.tool !== undefined) signable.tool = msg.tool;
  if (msg.request_id !== undefined) signable.request_id = msg.request_id;
  if (msg.params !== undefined) {
    const paramsJson = JSON.stringify(msg.params, Object.keys(msg.params).sort());
    signable.params_hash = _hash(Buffer.from(paramsJson, "utf-8")).toString("base64");
  }
  
  const sorted = {};
  Object.keys(signable).sort().forEach(k => { sorted[k] = signable[k]; });
  return JSON.stringify(sorted);
}

const debugScript = `
import sys, json, hashlib, base64
sys.path.insert(0, ${JSON.stringify(path.join(__dirname, "..", "..", "src", "twin_protocol"))})
from identity import AgentIdentity, _canonicalize

# Create identity
id_test = AgentIdentity("cross-test-py")
id_test.generate()

# Sign a message WITHOUT payload (to isolate)
msg1 = {
    "type": "tool_request",
    "source": "cross-test-py",
    "tool": "shell.run",
    "params": {"command": "echo hello"},
    "request_id": "cross-test-001",
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-001"
}

canonical1 = _canonicalize(msg1, "cross-test-py")
print("CANON1:" + canonical1.decode())

# Also sign it and get the full signed message
signed1 = id_test.sign(msg1)
print("SIGNED1:" + json.dumps(signed1, sort_keys=True))

# Check what signer value is used
print("SIGNER1:" + id_test.name)

# Test 2: message WITH payload
msg2 = {
    "type": "message",
    "source": "cross-test-py",
    "payload": {"text": "hello world"},
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-002"
}
canonical2 = _canonicalize(msg2, "cross-test-py")
print("CANON2:" + canonical2.decode())
`;

fs.writeFileSync(path.join(TEST_DIR, "debug2.py"), debugScript);
const output = execSync(`python "${path.join(TEST_DIR, "debug2.py")}"`, { encoding: "utf-8", timeout: 10000 });

const lines = {};
output.split("\n").forEach(line => {
  const colonIdx = line.indexOf(":");
  if (colonIdx > 0) {
    const key = line.substring(0, colonIdx);
    const val = line.substring(colonIdx + 1);
    lines[key] = val;
  }
});

if (lines["CANON1"]) {
  console.log("Python CANON1:", lines["CANON1"]);
  // Build equivalent msg without source
  const testMsg1 = {
    type: "tool_request",
    tool: "shell.run",
    params: { command: "echo hello" },
    request_id: "cross-test-001",
    timestamp: "2026-06-26T00:00:00Z",
    id: "cross-lang-001"
  };
  const nodeCanon1 = pythonCanonicalize(testMsg1, lines["SIGNER1"] || "cross-test-py");
  console.log("Node   CANON1:", nodeCanon1);
  console.log("MATCH1:", lines["CANON1"] === nodeCanon1 ? "YES" : "NO");
  
  if (lines["CANON1"] !== nodeCanon1) {
    for (let i = 0; i < Math.max(lines["CANON1"].length, nodeCanon1.length); i++) {
      if (lines["CANON1"][i] !== nodeCanon1[i]) {
        console.log(`  Diff at ${i}: Python="${lines["CANON1"][i] || "EOF"}" Node="${nodeCanon1[i] || "EOF"}"`);
        console.log(`  Py ctx: ${lines["CANON1"].substring(Math.max(0,i-5), i+15)}`);
        console.log(`  Nd ctx: ${nodeCanon1.substring(Math.max(0,i-5), i+15)}`);
        break;
      }
    }
  }
}

if (lines["CANON2"]) {
  console.log("\nPython CANON2:", lines["CANON2"]);
  const testMsg2 = {
    type: "message",
    source: "cross-test-py",
    payload: { text: "hello world" },
    timestamp: "2026-06-26T00:00:00Z",
    id: "cross-lang-002"
  };
  const nodeCanon2 = pythonCanonicalize(testMsg2, lines["SIGNER1"] || "cross-test-py");
  console.log("Node   CANON2:", nodeCanon2);
  console.log("MATCH2:", lines["CANON2"] === nodeCanon2 ? "YES" : "NO");
}
