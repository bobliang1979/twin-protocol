/**
 * cross-language-test.js
 * Twins Protocol Cross-Language Ed25519 Signature Verification
 * 
 * Tests bidirectional signing: Python ↔ Node.js
 * Both v0.1 (Python native) and v0.2 (unified no-space JSON) formats.
 * 
 * Usage: node cross-language-test.js
 */

const crypto = require("crypto");
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const PYTHON_SRC = path.join(ROOT, "src", "twin_protocol");
const TEST_DIR = path.join(__dirname, ".cross-test");
const PYTHON_EXE = "python";

let passed = 0, failed = 0;

function test(name, ok, detail) {
  if (ok) { passed++; console.log(`  ✅ ${name}`); }
  else { failed++; console.log(`  ❌ ${name}: ${detail || "FAILED"}`); }
}

/** Convert raw 32-byte Ed25519 key bytes to PEM for Node crypto */
function rawToPubKeyPem(rawBytes) {
  const pubKeyInfo = Buffer.concat([
    Buffer.from([0x30, 0x2a, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x03, 0x21, 0x00]),
    rawBytes
  ]);
  const b64 = pubKeyInfo.toString("base64");
  return "-----BEGIN PUBLIC KEY-----\n" + b64.match(/.{1,64}/g).join("\n") + "\n-----END PUBLIC KEY-----";
}

if (!fs.existsSync(TEST_DIR)) fs.mkdirSync(TEST_DIR, { recursive: true });

const script = `
import sys, json, base64, os
sys.path.insert(0, ${JSON.stringify(PYTHON_SRC)})
from identity import AgentIdentity, _canonicalize, _canonicalize_v02

# Generate identity (once, reuse for all tests)
id_test = AgentIdentity("cross-lang-test")
if not id_test.load():
    id_test.generate()

msg = {
    "type": "tool_request",
    "source": "cross-lang-test",
    "tool": "shell.run",
    "params": {"command": "echo cross-lang"},
    "request_id": "cross-lang-001",
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-001"
}

# v0.1 sign (with spaces in JSON)
signed_v01 = id_test.sign(msg)
canon_v01 = _canonicalize(msg, "cross-lang-test").decode().strip()

# v0.2 sign (no-space JSON)
signed_v02 = id_test.sign_v02(msg)
canon_v02 = _canonicalize_v02(msg, "cross-lang-test").decode().strip()

# Also message with payload
msg2 = {
    "type": "message",
    "source": "cross-lang-test",
    "payload": {"text": "Hello cross-lang!"},
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-002"
}
signed_v02b = id_test.sign_v02(msg2)

result = {
    "public_key_raw": base64.b64encode(id_test.public_key).decode(),
    "v01": {"canonical": canon_v01, "signed": signed_v01},
    "v02": {"canonical": canon_v02, "signed": signed_v02},
    "v02b": {"signed": signed_v02b}
}
print(json.dumps(result, ensure_ascii=False))
`;

fs.writeFileSync(path.join(TEST_DIR, "py_sign_all.py"), script);
const raw = execSync(`${PYTHON_EXE} "${path.join(TEST_DIR, "py_sign_all.py")}"`, { encoding: "utf-8", timeout: 10000 });
const pyData = JSON.parse(raw.trim());

console.log("\\n🔐 Cross-Language Ed25519 Signature Test");
console.log("=".repeat(60));
console.log("");

// ── Phase 1: Python v0.1 sign (spaces) → Node.js verify ──
console.log("─── Phase 1: Python v0.1 (spaces) → Node.js verify ───");
const pubKeyPem = rawToPubKeyPem(Buffer.from(pyData.public_key_raw, "base64"));
const v01Canon = pyData.v01.canonical;
const v01Sig = Buffer.from(pyData.v01.signed.signature, "base64");

try {
  const isValid = crypto.verify(null, Buffer.from(v01Canon, "utf-8"), pubKeyPem, v01Sig);
  test("Python v0.1 sign → Node.js verify", isValid);
} catch (e) {
  test("Python v0.1 sign → Node.js verify", false, e.message);
}

// ── Phase 2: Python v0.2 sign (no-space) → Node.js verify ──
console.log("\\n─── Phase 2: Python v0.2 (no-space) → Node.js verify ───");
const v02Canon = pyData.v02.canonical;
const v02Sig = Buffer.from(pyData.v02.signed.signature, "base64");

try {
  const isValid = crypto.verify(null, Buffer.from(v02Canon, "utf-8"), pubKeyPem, v02Sig);
  test("Python v0.2 sign → Node.js verify", isValid);
} catch (e) {
  test("Python v0.2 sign → Node.js verify", false, e.message);
}

// ── Phase 3: Python v0.2 with payload → Node.js verify ──
console.log("\\n─── Phase 3: Python v0.2 (with payload) → Node.js verify ───");
const v02b = pyData.v02b.signed;
const { createHash } = crypto;
function canonicalV02(msg, signer) {
  const payload = msg.payload || {};
  const signable = { type: msg.type || "message", source: signer, timestamp: msg.timestamp || "", id: msg.id || "" };
  if (Object.keys(payload).length > 0) {
    signable.payload_hash = createHash("sha256").update(JSON.stringify(payload)).digest().toString("base64");
  }
  const sorted = {};
  Object.keys(signable).sort().forEach(k => { sorted[k] = signable[k]; });
  return JSON.stringify(sorted);
}
const v02bCanon = canonicalV02(v02b, "cross-lang-test");
const v02bSig = Buffer.from(v02b.signature, "base64");

try {
  const isValid = crypto.verify(null, Buffer.from(v02bCanon, "utf-8"), pubKeyPem, v02bSig);
  test("Python v0.2 (payload) → Node.js verify", isValid);
} catch (e) {
  test("Python v0.2 (payload) → Node.js verify", false, e.message);
}

// ── Phase 4: Node.js → Python verify via subprocess ──
console.log("\\n─── Phase 4: Node.js sign → Python verify ───");
const { generateKeyPairSync } = crypto;
const { publicKey: nodePubPem, privateKey: nodePrivPem } = generateKeyPairSync("ed25519", {
  publicKeyEncoding: { type: "spki", format: "pem" },
  privateKeyEncoding: { type: "pkcs8", format: "pem" },
});

const nodeMsg = { type: "message", payload: { text: "Hello from Node.js!" }, timestamp: "2026-06-26T00:00:00Z", id: "cross-lang-003" };
const nodeCanon = canonicalV02(nodeMsg, "cross-test-node");
const nodeSig = crypto.sign(null, Buffer.from(nodeCanon, "utf-8"), nodePrivPem);

// Export raw key from PEM
const pubKeyDer = Buffer.from(nodePubPem.replace(/-----.*?-----/g, "").trim(), "base64");
const rawNodePubKey = pubKeyDer.subarray(pubKeyDer.length - 32);

const verifyScript = `
import sys, json, base64, os
sys.path.insert(0, ${JSON.stringify(PYTHON_SRC)})
from identity import AgentIdentity, _canonicalize_v02
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

raw_key = base64.b64decode("${rawNodePubKey.toString("base64")}")
sig = base64.b64decode("${nodeSig.toString("base64")}")
canonical = ${JSON.stringify(nodeCanon)}

pub = Ed25519PublicKey.from_public_bytes(raw_key)
try:
    pub.verify(sig, canonical.encode("utf-8"))
    print("VALID")
except Exception as e:
    print(f"INVALID: {e}")
`;

fs.writeFileSync(path.join(TEST_DIR, "py_verify.py"), verifyScript);
try {
  const verifyOut = execSync(`${PYTHON_EXE} "${path.join(TEST_DIR, "py_verify.py")}"`, { encoding: "utf-8", timeout: 10000 });
  test("Node.js v0.2 sign → Python verify", verifyOut.trim() === "VALID", verifyOut.trim());
} catch (e) {
  test("Node.js v0.2 sign → Python verify", false, e.message.substring(0, 200));
}

// ── Phase 5: Use twin-identity.js signV02 to test ──
console.log("\\n─── Phase 5: twin-identity.js signV02 + self-verify ───");
const { AgentIdentity } = require("./twin-identity.js");
const codex = new AgentIdentity("codex-test-v02");
codex.ensure();

const testMsg = { type: "tool_request", tool: "shell.run", params: { command: "ls" }, request_id: "r1", timestamp: "2026-06-26T00:00:00Z", id: "sig-001" };
const signedMsg = codex.signV02(testMsg);
const verifyResult = codex.verify(signedMsg);
test("twin-identity.js signV02 self-verify", verifyResult.valid, verifyResult.keyId);

// ── Report ──
const total = passed + failed;
console.log("\\n" + "=".repeat(60));
console.log(`  ${passed}/${total} cross-language tests passed`);
if (failed > 0) {
  console.log(`  ❌ Failed: ${failed} tests`);
  process.exit(1);
} else {
  console.log(`  ✅ ALL CROSS-LANGUAGE TESTS PASSED`);
  console.log("");
  console.log("  Architecture decision: v0.2 canonicalization = no-space JSON");
  console.log("  Both Python and Node.js produce identical signatures.");
}

// Cleanup
try { fs.rmSync(TEST_DIR, { recursive: true, force: true }); } catch(e) {}
