/**
 * twin-protocol — Twins Protocol for Node.js
 *
 * Usage:
 *   const tp = require('twin-protocol');
 *   const identity = tp.createIdentity('my-agent');
 *
 *   // Sign a message
 *   const signed = identity.sign({ type: 'message', payload: { text: 'hello' } });
 *
 *   // Verify
 *   const result = tp.verify(signed, { 'my-agent': identity.publicKey });
 *   console.log(result.valid); // true
 *
 *   // Validate JSONL
 *   const errors = tp.validate('path/to/outbox.jsonl');
 *
 *   // HTTP Transport
 *   const server = tp.createServer({ tools: demo_tools });
 *   server.listen(3738);
 */

const { AgentIdentity, verifyMiddleware } = require('./twin-identity.js');
const { validate } = require('./twins-validate.js');
const { createHTTPServer } = require('./twins-http-server.js');

module.exports = {
  AgentIdentity,
  verify: verifyMiddleware,
  validate,
  createServer: createHTTPServer,
  version: '0.1.0',
  protocolVersion: '0.1',
};
