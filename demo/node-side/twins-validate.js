/**
 * twins-validate.js — Twins Protocol Validator
 * 
 * Validates a JSONL outbox against the Twins Protocol schemas.
 * 
 * Usage: node twins-validate.js <outbox-path>
 *        node twins-validate.js <outbox-path> --verbose
 */

const fs = require("fs");
const path = require("path");

const OUTBOX = process.argv[2] || "codex_outbox.jsonl";
const VERBOSE = process.argv.includes("--verbose") || process.argv.includes("-v");

// ── Schema validators (lightweight, no dependency needed) ──────────────────
const SCHEMAS = {
  message: {
    required: ["type", "source", "timestamp", "id", "payload"],
    fields: {
      type: v => v === "message",
      source: v => typeof v === "string" && v.length > 0,
      target: v => typeof v === "string",
      timestamp: v => typeof v === "string" && !isNaN(Date.parse(v)),
      id: v => typeof v === "string" && v.length >= 8,
      "payload.text": v => typeof v === "string",
      "payload.reply_to": v => v === undefined || typeof v === "string"
    }
  },
  tool_request: {
    required: ["type", "source", "request_id", "tool", "params"],
    fields: {
      type: v => v === "tool_request",
      source: v => typeof v === "string",
      request_id: v => typeof v === "string" && v.length >= 4,
      tool: v => ["shell.run", "file.read", "file.write", "screenshot", "memory.read", "skill_view", "js.eval", "workspace.read"].includes(v),
      params: v => typeof v === "object" && v !== null && !Array.isArray(v)
    }
  },
  tool_result: {
    required: ["type", "source", "request_id", "tool"],
    fields: {
      type: v => v === "tool_result",
      source: v => typeof v === "string",
      request_id: v => typeof v === "string",
      tool: v => typeof v === "string",
      result: v => v === null || typeof v === "object",
      error: v => v === null || typeof v === "string" || (typeof v === "object" && v !== null),
      execution_ms: v => v === undefined || (typeof v === "number" && v >= 0),
      _ts: v => v === undefined || (typeof v === "string")
    }
  },
  state_update: {
    required: ["type", "source", "timestamp", "state"],
    fields: {
      type: v => v === "state_update",
      source: v => typeof v === "string",
      timestamp: v => typeof v === "string" && !isNaN(Date.parse(v)),
      "state.phase": v => typeof v === "string",
      "state.last_reply_ts": v => v === undefined || (typeof v === "string")
    }
  }
};

const KNOWN_TYPES = Object.keys(SCHEMAS);
const VALID_TOOLS = ["shell.run", "file.read", "file.write", "screenshot", "memory.read", "skill_view", "js.eval", "workspace.read"];

// ── Validator ──────────────────────────────────────────────────────────────
function validateMessage(msg, lineNum) {
  const errors = [];
  const warnings = [];
  const type = msg && msg.type;

  // Unknown type
  if (!KNOWN_TYPES.includes(type)) {
    errors.push(`Unknown message type: "${type}"`);
    return { valid: false, errors, warnings, type: type || "unknown" };
  }

  const schema = SCHEMAS[type];

  // Required fields
  for (const field of schema.required) {
    const val = getNested(msg, field);
    if (val === undefined || val === null) {
      errors.push(`Missing required field: "${field}"`);
    }
  }

  // Field validations
  for (const [field, validator] of Object.entries(schema.fields)) {
    const val = getNested(msg, field);
    if (val !== undefined && !validator(val)) {
      warnings.push(`Invalid value for "${field}": ${JSON.stringify(val)}`);
    }
  }

  // Tool-specific checks
  if (type === "tool_request" && msg.tool && !VALID_TOOLS.includes(msg.tool)) {
    warnings.push(`Unknown tool: "${msg.tool}". Valid: ${VALID_TOOLS.join(", ")}`);
  }

  if (type === "tool_result" && msg.result && typeof msg.result === "object") {
    // Check for common result formats
    if (msg.result.stdout === undefined && msg.result.content === undefined) {
      // Non-standard result format - just a warning
    }
  }

  // Consistency checks
  if (type === "tool_result" && msg.request_id === "0") {
    warnings.push('Unusual request_id: "0"');
  }

  return { valid: errors.length === 0, errors, warnings, type };
}

function getNested(obj, path) {
  const parts = path.split(".");
  let current = obj;
  for (const part of parts) {
    if (current === null || current === undefined) return undefined;
    current = current[part];
  }
  return current;
}

// ── Main ──────────────────────────────────────────────────────────────────
function main() {
  if (!fs.existsSync(OUTBOX)) {
    console.error(`❌ File not found: ${OUTBOX}`);
    console.error(`Usage: node twins-validate.js <outbox-path>`);
    process.exit(1);
  }

  const raw = fs.readFileSync(OUTBOX, "utf-8");
  const lines = raw.trim().split("\n").filter(Boolean);
  
  console.log(`\n  Twins Protocol Validator`);
  console.log(`  File: ${OUTBOX}`);
  console.log(`  Lines: ${lines.length}`);
  console.log("");

  let valid = 0, invalid = 0;
  const byType = {};
  const allErrors = [];
  const allWarnings = [];

  lines.forEach((line, i) => {
    let msg;
    try {
      msg = JSON.parse(line);
    } catch (e) {
      invalid++;
      const err = `Line ${i + 1}: Invalid JSON — ${e.message}`;
      allErrors.push(err);
      if (VERBOSE) console.log(`  ${err}`);
      return;
    }

    const result = validateMessage(msg, i + 1);
    const t = result.type || "unknown";
    byType[t] = (byType[t] || 0) + 1;

    if (result.valid) {
      valid++;
    } else {
      invalid++;
      result.errors.forEach(e => {
        const err = `Line ${i + 1} [${t}]: ${e}`;
        allErrors.push(err);
        if (VERBOSE) console.log(`  ❌ ${err}`);
      });
    }

    result.errors.forEach(w => {
      const warn = `Line ${i + 1} [${t}]: ${w}`;
      allWarnings.push(warn);
      if (VERBOSE) console.log(`  ⚠️  ${warn}`);
    });
  });

  // Summary
  console.log("  ─────────────────────────────────");
  console.log(`  ✅ Valid:   ${valid}`);
  console.log(`  ❌ Invalid: ${invalid}`);
  console.log(`  ⚠️  Warnings: ${allWarnings.length}`);
  console.log("");

  if (Object.keys(byType).length > 0) {
    console.log("  By type:");
    Object.entries(byType)
      .sort((a, b) => b[1] - a[1])
      .forEach(([t, c]) => {
        const schema = SCHEMAS[t];
        const icon = schema ? "✓" : "?";
        console.log(`    ${icon} ${t}: ${c}`);
      });
    console.log("");
  }

  if (allErrors.length > 0 && !VERBOSE) {
    console.log(`  ${allErrors.length} error(s). Use --verbose to see details.`);
  }

  if (allWarnings.length > 0 && !VERBOSE) {
    console.log(`  ${allWarnings.length} warning(s). Use --verbose to see details.`);
  }

  process.exit(invalid > 0 ? 1 : 0);
}

if (require.main === module) { main(); }

// Export for use by twins-test.js
module.exports = { validateMessage, SCHEMAS, KNOWN_TYPES, VALID_TOOLS, getNested };


// Export for use by twins-test.js
module.exports = { validateMessage, SCHEMAS, KNOWN_TYPES, VALID_TOOLS, getNested };
