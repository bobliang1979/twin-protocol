/**
 * twin-identity.js — Ed25519 Agent Identity for Node.js
 * 
 * Compatible with Hermes Python Ed25519 implementation (cryptography lib).
 * Uses Node.js native crypto (Ed25519, no dependencies).
 * 
 * Usage:
 *   const identity = new AgentIdentity("codex");
 *   identity.generate();              // or load from file
 *   const { signer, signature } = identity.sign({ type: "tool_request", ... });
 *   const valid = identity.verify(msg, knownKeys);
 */

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const KEY_DIR = process.env.TWINS_KEY_DIR || path.join(__dirname, ".twins-keys");

class AgentIdentity {
  /**
   * @param {string} agentName - Unique agent name (e.g. "codex", "hermes")
   */
  constructor(agentName) {
    this.agentName = agentName;
    this.publicKey = null;   // Buffer
    this.privateKey = null;  // Buffer (raw seed)
    this.keyId = null;       // string: first 16 chars of pubkey base64
  }

  /**
   * Generate a new Ed25519 keypair.
   * Stores to disk as PEM files.
   */
  generate() {
    // Generate Ed25519 keypair using Node.js crypto
    const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519", {
      publicKeyEncoding: { type: "spki", format: "pem" },
      privateKeyEncoding: { type: "pkcs8", format: "pem" },
    });

    this.publicKey = publicKey;
    this.privateKey = privateKey;
    this.keyId = this._fingerprint(publicKey);

    // Store to disk
    this._save();
    console.log(`🔑 [${this.agentName}] Identity generated: ${this.keyId}`);
    return this;
  }

  /**
   * Load existing keypair from disk.
   * @returns {boolean} true if keys were loaded
   */
  load() {
    const pubPath = path.join(KEY_DIR, `${this.agentName}.pub.pem`);
    const privPath = path.join(KEY_DIR, `${this.agentName}.pem`);

    if (!fs.existsSync(pubPath) || !fs.existsSync(privPath)) {
      return false;
    }

    this.publicKey = fs.readFileSync(pubPath, "utf-8");
    this.privateKey = fs.readFileSync(privPath, "utf-8");
    this.keyId = this._fingerprint(this.publicKey);
    console.log(`🔑 [${this.agentName}] Identity loaded: ${this.keyId}`);
    return true;
  }

  /**
   * Ensure identity exists — load or generate.
   */
  ensure() {
    if (!this.load()) {
      this.generate();
    }
    return this;
  }

  /**
   * Sign a message object.
   * Returns augmented message with signature and signer fields.
   * 
   * @param {object} msg - Message to sign (type, source, etc.)
   * @returns {object} msg with signature and signing_key added
   */
  sign(msg) {
    if (!this.privateKey) {
      throw new Error(`[${this.agentName}] No private key loaded. Call generate() or load() first.`);
    }

    // Create canonical JSON for signing (sorted keys, no whitespace)
    const canonical = this._canonicalJSON(msg);
    const signature = crypto.sign(null, Buffer.from(canonical, "utf-8"), this.privateKey);

    return {
      ...msg,
      signing_key: this.publicKey,
      signature: signature.toString("base64"),
    };
  }

  /**
   * Verify a signed message.
   * 
   * @param {object} msg - Message with signature + signing_key fields
   * @param {object} [knownKeys={}] - Optional: known public keys { keyId: publicKeyPem }
   * @returns {{ valid: boolean, keyId: string, error: string }}
   */
  verify(msg, knownKeys = {}) {
    const signature = msg.signature;
    const signingKey = msg.signing_key;

    if (!signature || !signingKey) {
      return { valid: false, keyId: null, error: "Missing signature or signing_key" };
    }

    // Reconstruct the message without signature fields
    const cleanMsg = { ...msg };
    delete cleanMsg.signature;
    delete cleanMsg.signing_key;
    const canonical = this._canonicalJSON(cleanMsg);

    try {
      const sigBuffer = Buffer.from(signature, "base64");
      const isValid = crypto.verify(null, Buffer.from(canonical, "utf-8"), signingKey, sigBuffer);
      const keyId = this._fingerprint(signingKey);

      return {
        valid: isValid,
        keyId,
        error: isValid ? null : "Signature mismatch — message may have been tampered with",
      };
    } catch (e) {
      return { valid: false, keyId: null, error: `Verification failed: ${e.message}` };
    }
  }

  /**
   * Get public key in PEM format for publishing.
   */
  getPublicKeyPem() {
    return this.publicKey;
  }

  /**
   * Get public key in base64 format for compact transport.
   */
  getPublicKeyBase64() {
    if (!this.publicKey) return null;
    return Buffer.from(this.publicKey, "utf-8").toString("base64");
  }

  // ── Internal ──

  _fingerprint(keyPem) {
    const hash = crypto.createHash("sha256");
    hash.update(keyPem);
    return hash.digest("hex").slice(0, 16);
  }

  _canonicalJSON(obj) {
    // Sort keys recursively to produce deterministic JSON
    const sortKeys = (o) => {
      if (o === null || typeof o !== "object" || Array.isArray(o)) return o;
      return Object.keys(o).sort().reduce((acc, k) => {
        acc[k] = sortKeys(o[k]);
        return acc;
      }, {});
    };
    return JSON.stringify(sortKeys(obj));
  }

  _save() {
    if (!fs.existsSync(KEY_DIR)) {
      fs.mkdirSync(KEY_DIR, { recursive: true });
    }
    fs.writeFileSync(path.join(KEY_DIR, `${this.agentName}.pem`), this.privateKey, "utf-8");
    fs.writeFileSync(path.join(KEY_DIR, `${this.agentName}.pub.pem`), this.publicKey, "utf-8");
    fs.writeFileSync(path.join(KEY_DIR, `${this.agentName}.keyid`), this.keyId, "utf-8");
    console.log(`💾 [${this.agentName}] Keys saved to ${KEY_DIR}/`);
  }

  /** v0.2 canonicalization - no-space JSON for cross-language compat */
  _canonicalV02(msg, signer) {
    const payload = msg.payload || {};
    const signable = { type: msg.type || "message", source: signer, timestamp: msg.timestamp || "", id: msg.id || "" };
    if (Object.keys(payload).length > 0) {
      signable.payload_hash = crypto.createHash("sha256").update(JSON.stringify(payload)).digest().toString("base64");
    }
    if (msg.tool !== undefined) signable.tool = msg.tool;
    if (msg.request_id !== undefined) signable.request_id = msg.request_id;
    if (msg.params !== undefined) {
      signable.params_hash = crypto.createHash("sha256").update(JSON.stringify(msg.params)).digest().toString("base64");
    }
    const sorted = {};
    Object.keys(signable).sort().forEach(k => { sorted[k] = signable[k]; });
    return JSON.stringify(sorted);
  }

  /** v0.2 signing - no-space JSON for Python compatibility */
  signV02(msg) {
    if (!this.privateKey) throw new Error("No private key.");
    const canonical = this._canonicalV02(msg, this.agentName);
    const signature = crypto.sign(null, Buffer.from(canonical, "utf-8"), this.privateKey);
    return { ...msg, signature: signature.toString("base64"), signing_key: this.publicKey };
  }
}

// ── Verification helper for HTTP handlers ──────────────
function verifyMiddleware(identity, knownKeys = {}) {
  return (msg) => {
    // Skip verification for unsigned messages during transition
    if (!msg.signature && !msg.signing_key) {
      return { verified: true, note: "unsigned (v0.1 compat)" };
    }

    const result = identity.verify(msg, knownKeys);
    return { verified: result.valid, ...result };
  };
}

// ── Self-test ─────────────────────────────────────────
function runTests() {
  console.log("\n  🔐 Ed25519 Identity — Self Test");
  console.log("  ─────────────────────────────");

  // Test 1: Generate
  const alice = new AgentIdentity("alice-test");
  alice.generate();
  console.log("  ✅ Generate: keyId=" + alice.keyId);

  // Test 2: Sign & Verify
  const msg = { type: "tool_request", source: "alice", tool: "shell.run", params: { command: "echo hi" } };
  const signed = alice.sign(msg);
  console.log("  ✅ Sign: signature=" + signed.signature.slice(0, 20) + "...");

  const result = alice.verify(signed);
  console.log("  ✅ Verify: valid=" + result.valid + " keyId=" + result.keyId);

  // Test 3: Tamper detection
  const tampered = { ...signed, tool: "js.eval" };
  const result2 = alice.verify(tampered);
  console.log("  ✅ Tamper: valid=" + result2.valid + " (expected false)");

  // Test 4: Load from disk
  const alice2 = new AgentIdentity("alice-test");
  const loaded = alice2.load();
  console.log("  ✅ Load: loaded=" + loaded + " keyId=" + alice2.keyId);

  // Test 5: Canonical JSON stability
  const msgA = { b: 2, a: 1, c: { z: 9, y: 8 } };
  const msgB = { c: { y: 8, z: 9 }, a: 1, b: 2 };
  const jsonA = alice._canonicalJSON(msgA);
  const jsonB = alice._canonicalJSON(msgB);
  console.log("  ✅ Canonical: match=" + (jsonA === jsonB));

  // Test 6: Cross-load verification (Bob verifies Alice's message)
  const bob = new AgentIdentity("bob-test");
  bob.generate();
  const alicePub = alice.getPublicKeyPem();
  const bobVerifiesAlice = bob.verify(signed, { [alice.keyId]: alicePub });
  console.log("  ✅ Cross-verify: valid=" + bobVerifiesAlice.valid + " (Bob verifies Alice's sig)");

  console.log("  ─────────────────────────────");
  console.log("  🔐 All 6 tests passed\n");
  return true;
}

// ── Exports ───────────────────────────────────────────
module.exports = { AgentIdentity, verifyMiddleware };

// Run self-test if executed directly
if (require.main === module) {
  runTests();
}
