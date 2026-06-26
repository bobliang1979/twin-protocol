const crypto = require("crypto");
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const TEST_DIR = path.join(__dirname, ".cross-test");
if (!fs.existsSync(TEST_DIR)) fs.mkdirSync(TEST_DIR, { recursive: true });

/**
 * Python-compatible canonicalization.
 * Python json.dumps(sort_keys=True) uses "key": value (with space after colon)
 * Node JSON.stringify uses "key":value (no space)
 * 
 * We build the JSON string manually to match Python's format.
 */
function pyStyleJson(obj) {
  if (obj === null || obj === undefined) return "null";
  if (typeof obj === "string") return JSON.stringify(obj);
  if (typeof obj === "number" || typeof obj === "boolean") return String(obj);
  if (Array.isArray(obj)) {
    const items = obj.map(pyStyleJson);
    return "[" + items.join(", ") + "]";
  }
  if (typeof obj === "object") {
    const keys = Object.keys(obj).sort();
    const pairs = keys.map(k => `${JSON.stringify(k)}: ${pyStyleJson(obj[k])}`);
    return "{" + pairs.join(", ") + "}";
  }
  return String(obj);
}

// Python's exact hashing
function pyHash(data) {
  return crypto.createHash("sha256").update(Buffer.from(data, "utf-8")).digest();
}

function pythonCanonicalizeExact(msg, signer) {
  const signerClean = signer.trim(); // Windows CRLF fix
  const payload = (msg.payload !== undefined && msg.payload !== null) ? msg.payload : {};
  const signable = {
    type: msg.type || "message",
    source: signerClean,
    timestamp: msg.timestamp || "",
    id: msg.id || "",
  };
  
  const hasPayload = typeof payload === "object" && Object.keys(payload).length > 0;
  if (hasPayload) {
    const payloadJson = pyStyleJson(payload);
    signable.payload_hash = pyHash(payloadJson).toString("base64");
  }
  
  if (msg.tool !== undefined) signable.tool = msg.tool;
  if (msg.request_id !== undefined) signable.request_id = msg.request_id;
  if (msg.params !== undefined) {
    const paramsJson = pyStyleJson(msg.params);
    signable.params_hash = pyHash(paramsJson).toString("base64");
  }
  
  return pyStyleJson(signable);
}

// Test it
const testMsg1 = {
  type: "tool_request",
  tool: "shell.run",
  params: {command: "echo hello"},
  request_id: "cross-test-001",
  timestamp: "2026-06-26T00:00:00Z",
  id: "cross-lang-001"
};

const debugScript = `
import sys, json
sys.path.insert(0, ${JSON.stringify(path.join(__dirname, "..", "..", "src", "twin_protocol"))})
from identity import _canonicalize

msg1 = {
    "type": "tool_request",
    "source": "cross-test-py",
    "tool": "shell.run",
    "params": {"command": "echo hello"},
    "request_id": "cross-test-001",
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-001"
}

canon1 = _canonicalize(msg1, "cross-test-py")
print("C:" + canon1.decode())
`;

fs.writeFileSync(path.join(TEST_DIR, "debug3.py"), debugScript);
const output = execSync(`python "${path.join(TEST_DIR, "debug3.py")}"`, { encoding: "utf-8", timeout: 10000 });
const pyCanon = output.split("\n").find(l => l.startsWith("C:")).substring(2);

console.log("Python canonical:", pyCanon);
const nodeCanon = pythonCanonicalizeExact(testMsg1, "cross-test-py");
console.log("Node   canonical:", nodeCanon);
console.log("MATCH:", pyCanon === nodeCanon ? "YES" : "NO");

if (pyCanon !== nodeCanon) {
  for (let i = 0; i < Math.max(pyCanon.length, nodeCanon.length); i++) {
    if (pyCanon[i] !== nodeCanon[i]) {
      console.log(`  Diff at ${i}: Py="${pyCanon[i] || "EOF"}" Nd="${nodeCanon[i] || "EOF"}"`);
      break;
    }
  }
}
