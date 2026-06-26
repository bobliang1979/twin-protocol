/**
 * cross-language-sign-test.js
 * Twins Protocol Cross-Language Ed25519 Signature Verification Test
 *
 * Tests: Python signs → Node.js verifies AND Node.js signs → Python verifies
 *
 * Compatibility bridge: Both sides must use the same canonicalization format.
 * We extend Node.js AgentIdentity.verify() to support the Python canonical format.
 */

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..", "..");
const PYTHON_SRC = path.join(ROOT, "src", "twin_protocol");
const NODE_SRC = path.join(__dirname);
const TEST_DIR = path.join(__dirname, ".cross-test");
const PYTHON_EXE = "python";

let passed = 0, failed = 0;

function test(name, ok, detail) {
  if (ok) { passed++; console.log(`  ✅ ${name}`); }
  else { failed++; console.log(`  ❌ ${name}: ${detail || "FAILED"}`); }
}

/**
 * Convert raw bytes (Buffer) to PEM format for crypto.verify
 * Ed25519 raw keys are 32 bytes
 */
function rawToPublicKeyPem(rawBytes) {
  if (Buffer.isBuffer(rawBytes) && rawBytes.length === 32) {
    // Wrap raw key in SPKI DER structure
    const pubKeyInfo = Buffer.concat([
      Buffer.from([0x30, 0x2a, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70,
                    0x03, 0x21, 0x00]),
      rawBytes
    ]);
    const b64 = pubKeyInfo.toString("base64");
    return `-----BEGIN PUBLIC KEY-----\n${b64.match(/.{1,64}/g).join("\n")}\n-----END PUBLIC KEY-----`;
  }
  return rawBytes.toString("utf-8");
}

/**
 * Python-style canonicalization for signing.
 * Builds a subset dict with specific fields + hashes of payload/params.
 */
function pythonCanonicalize(msg, signer) {
  const payload = msg.payload || {};
  const signable = {
    type: msg.type || "message",
    source: signer,
    timestamp: msg.timestamp || "",
    id: msg.id || "",
  };
  if (Object.keys(payload).length > 0) {
    const hash = crypto.createHash("sha256").update(JSON.stringify(payload, Object.keys(payload).sort())).digest();
    signable.payload_hash = hash.toString("base64");
  }
  if (msg.tool) signable.tool = msg.tool;
  if (msg.request_id) signable.request_id = msg.request_id;
  if (msg.params) {
    const hash = crypto.createHash("sha256").update(JSON.stringify(msg.params, Object.keys(msg.params).sort())).digest();
    signable.params_hash = hash.toString("base64");
  }
  return JSON.stringify(Object.keys(signable).sort().reduce((o, k) => { o[k] = signable[k]; return o; }, {}));
}

/**
 * Node.js-style canonicalization: full message minus signature fields, sorted keys.
 */
function nodeCanonicalize(msg) {
  const sortKeys = (o) => {
    if (o === null || typeof o !== "object" || Array.isArray(o)) return o;
    return Object.keys(o).sort().reduce((acc, k) => { acc[k] = sortKeys(o[k]); return acc; }, {});
  };
  const clean = { ...msg };
  delete clean.signature;
  delete clean.signing_key;
  delete clean.signer;
  return JSON.stringify(sortKeys(clean));
}

async function runTests() {
  console.log("\n🔐 Cross-Language Ed25519 Signature Verification Test");
  console.log("  Testing: Python ↔ Node.js signature interoperability");
  console.log("=".repeat(60));
  console.log("");

  console.log("─── Phase 1: Python signs, Node.js verifies ───");

  // Step 1: Generate Python keypair and sign a test message
  const pythonScript = `
import sys, json, base64, os
sys.path.insert(0, ${JSON.stringify(PYTHON_SRC)})
from identity import AgentIdentity

# Create test identity
id_test = AgentIdentity("cross-test-py")
id_test.generate()

# Sign a message
msg = {
    "type": "tool_request",
    "source": "cross-test-py",
    "tool": "shell.run",
    "params": {"command": "echo hello"},
    "request_id": "cross-test-001",
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-001"
}
signed = id_test.sign(msg)

# Output key and signature for Node.js to verify
result = {
    "public_key_raw": base64.b64encode(id_test.public_key).decode(),
    "signed_message": signed,
    "key_id": id_test.public_key.hex()[:16]
}
print(json.dumps(result))
`;

  fs.writeFileSync(path.join(TEST_DIR, "py_sign.py"), pythonScript);
  
  try {
    const rawOutput = execSync(`${PYTHON_EXE} "${path.join(TEST_DIR, "py_sign.py")}"`, {
      encoding: "utf-8",
      timeout: 10000,
    });
    const pyResult = JSON.parse(rawOutput.trim());
    test("Python key generation + signing works", !!pyResult.signed_message.signature, pyResult.key_id);
    test("Python includes signer field", pyResult.signed_message.signer === "cross-test-py");
    test("Python includes signature in output", pyResult.signed_message.signature.length > 40);

    // Step 2: Node.js verifies using Python's canonicalization
    const pythonMsg = pyResult.signed_message;
    const pubKeyRaw = Buffer.from(pyResult.public_key_raw, "base64");
    const pubKeyPem = rawToPublicKeyPem(pubKeyRaw);
    
    // Reconstruct canonical form using Python's algorithm
    const canonicalMsg = pythonCanonicalize(pythonMsg, pythonMsg.signer);
    const signature = Buffer.from(pythonMsg.signature, "base64");
    
    const isValid = crypto.verify(null, Buffer.from(canonicalMsg, "utf-8"), pubKeyPem, signature);
    test("Node.js verifies Python signature (Python canonical form)", isValid, 
         isValid ? "signature valid" : "SIGNATURE MISMATCH");

    // Step 3: Also try Node.js canonical form
    const nodeCanonical = nodeCanonicalize(pythonMsg);
    const isValidNode = crypto.verify(null, Buffer.from(nodeCanonical, "utf-8"), pubKeyPem, signature);
    test("Node.js verifies Python signature (Node canonical form - may differ)", 
         isValidNode, 
         `Python canonical=${isValid} Node canonical=${isValidNode}`);

  } catch (e) {
    test("Python signing phase", false, e.message.substring(0, 200));
  }

  console.log("");
  console.log("─── Phase 2: Node.js signs, Python verifies ───");

  // Step 4: Generate Node.js keypair and sign
  const { generateKeyPairSync, sign, createHash } = crypto;
  const { publicKey: nodePubKey, privateKey: nodePrivKey } = generateKeyPairSync("ed25519", {
    publicKeyEncoding: { type: "spki", format: "pem" },
    privateKeyEncoding: { type: "pkcs8", format: "pem" },
  });

  const nodeMsg = {
    type: "message",
    source: "cross-test-node",
    payload: { text: "Hello from Node.js, verifying cross-language signing!" },
    timestamp: "2026-06-26T00:00:00Z",
    id: "cross-lang-002"
  };

  // Sign using Node.js native canonical form
  const nodeCanonical = nodeCanonicalize(nodeMsg);
  const nodeSignature = sign(null, Buffer.from(nodeCanonical, "utf-8"), nodePrivKey);

  // Also produce Python-canonical signature for verification
  const pyCanonical = pythonCanonicalize(nodeMsg, "cross-test-node");
  const pyCanonicalSignature = sign(null, Buffer.from(pyCanonical, "utf-8"), nodePrivKey);
  
  const nodeKeyId = createHash("sha256").update(nodePubKey).digest("hex").slice(0, 16);
  test("Node.js key generation + signing works", nodeSignature.length > 0, nodeKeyId);

  // Step 5: Export PEM public key and have Python verify
  const pubKeyB64 = Buffer.from(nodePubKey, "utf-8").toString("base64");

  const verifyScript = `
import sys, json, base64
sys.path.insert(0, ${JSON.stringify(PYTHON_SRC)})
from identity import AgentIdentity

# Python verifies Node.js signature using Python's canonical form
pub_key_b64 = ${JSON.stringify(pubKeyB64)}
signature_b64 = ${JSON.stringify(pyCanonicalSignature.toString("base64"))}
msg = ${JSON.stringify(nodeMsg)}

# Reconstruct signed message with Python-style fields
signed = dict(msg)
signed["signer"] = "cross-test-node"
signed["signature"] = signature_b64

# Python's verify_message needs raw bytes for public key.
# Parse the PEM to extract raw key bytes
from cryptography.hazmat.primitives.serialization import load_pem_public_key, Encoding, PublicFormat
pem_bytes = base64.b64decode(pub_key_b64)
pub_key = load_pem_public_key(pem_bytes)
raw_key = pub_key.public_bytes(Encoding.Raw, PublicFormat.Raw)

# Add to known_keys
known_keys = {"cross-test-node": raw_key}
result = AgentIdentity.verify_message(signed, known_keys=known_keys)
print(f"verified={result.valid} error={result.error}")
`;

  fs.writeFileSync(path.join(TEST_DIR, "py_verify.py"), verifyScript);

  try {
    const verifyOutput = execSync(`${PYTHON_EXE} "${path.join(TEST_DIR, "py_verify.py")}"`, {
      encoding: "utf-8",
      timeout: 10000,
    });
    const verified = verifyOutput.trim().includes("verified=True");
    test("Python verifies Node.js signature (Python canonical form)", verified, verifyOutput.trim());
  } catch (e) {
    test("Python verification phase", false, e.message.substring(0, 200));
  }

  // Step 6: Self-verify Node.js signs with its own canonical form
  const selfVerify = crypto.verify(
    null,
    Buffer.from(nodeCanonical, "utf-8"),
    nodePubKey,
    nodeSignature
  );
  test("Node.js self-verify (Node canonical form)", selfVerify);

  // Cleanup
  try {
    fs.rmSync(TEST_DIR, { recursive: true, force: true });
    // But don't remove the directory itself, we might need it
  } catch (e) {}

  // Report
  const total = passed + failed;
  console.log("\n" + "=".repeat(60));
  console.log(`  ${passed}/${total} cross-language tests passed`);
  if (failed > 0) {
    console.log(`  ❌ Failed: ${failed} test(s)`);
    process.exit(1);
  } else {
    console.log(`  ✅ ALL CROSS-LANGUAGE TESTS PASSED`);
    console.log("");
    console.log("  Key finding: Python and Node.js use DIFFERENT canonicalization formats.");
    console.log("  v0.2 must standardize on ONE format for cross-language interoperability.");
    console.log("  Recommended: Adopt Python's subset-hash approach (more secure, no full payload exposure).");
  }
}

// Ensure test dir exists
if (!fs.existsSync(TEST_DIR)) fs.mkdirSync(TEST_DIR, { recursive: true });

runTests().catch(e => {
  console.error(`\n  ❌ Test runner crashed: ${e.message}`);
  process.exit(1);
});
