#!/usr/bin/env node
/**
 * twins CLI — Twins Protocol command-line interface
 * Usage: twins <command> [options]
 */
const { AgentIdentity } = require("./twin-identity.js");
const { execSync } = require("child_process");

const cmd = process.argv[2];
switch (cmd) {
  case "init":
    const id = new AgentIdentity("default");
    id.ensure();
    console.log("Identity created:", id.keyId);
    break;
  case "validate":
    const { twinsValidate } = require("./twins-validate.js");
    break;
  case "demo":
    require("./twins-solo.js");
    break;
  default:
    console.log("Usage: twins init|validate|demo");
}
