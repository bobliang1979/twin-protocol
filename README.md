<div align="center">

![Twins Protocol Demo](assets/demo.gif)


# 🧬 Twins Protocol

### `pip install twin-protocol && twins demo`

**Two AI agents. One JSONL file. Zero infrastructure.**

[![PyPI](https://img.shields.io/pypi/v/twin-protocol?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/twin-protocol/)
[![npm](https://img.shields.io/npm/v/twin-protocol?style=flat-square&logo=npm&logoColor=white)](https://www.npmjs.com/package/twin-protocol)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg?style=flat-square&logo=node.js&logoColor=white)](https://nodejs.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://github.com/bobliang1979/twin-protocol/pulls)
[![CI](https://github.com/bobliang1979/twin-protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/bobliang1979/twin-protocol/actions/workflows/ci.yml)

</div>

---

## ⚡ 10 Seconds

```bash
pip install twin-protocol
twins demo
# → Opens browser at http://localhost:3737
# → Two AI agents discover each other and start collaborating
```

Or with Docker:

```bash
docker compose up
# → Two AI agents. One shared file. Zero config.
```

---

## 🧬 What is Twins Protocol?

**MCP connects one AI to its tools. Twins connects any AI to any other AI's tools.**

A minimal, file-based protocol where AI agents discover each other, sign messages with Ed25519, and trade abilities through nothing but a shared JSONL file.

```
┌─────────────────┐         codex_outbox.jsonl         ┌─────────────────┐
│                 │ ─── tool_request ──────────────▶  │                 │
│   Agent A       │ ◀── tool_result ────────────────  │   Agent B       │
│   (Python)      │ ─── state_update ───────────────▶  │   (Node.js)     │
│                 │ ◀── message ────────────────────  │                 │
└─────────────────┘                                    └─────────────────┘
```

| Feature | What it means |
|---------|--------------|
| **File as IPC** | No Redis, no gRPC, no message broker. A JSONL file is the bus |
| **Ed25519 identity** | Every message signed. No central registry needed |
| **Cross-language** | Python signs, Node.js verifies. Works across any stack |
| **Append-only ledger** | Every agent decision is auditable & replayable |
| **Zero infrastructure** | A file, two agents, and a shared folder. That'\''s it |

This is **MCP in reverse**. MCP = AI → tools. Twins = AI ↔ AI. Every agent'\''s plugin becomes every agent'\''s plugin.

---

## 🚀 Quick Start

### pip install (Python)

```bash
pip install twin-protocol
twins init            # Create identity keys
twins validate outbox.jsonl  # Validate protocol compliance
twins demo            # Launch solo demo
```

### npm install (Node.js)

```bash
npm install @bobliang1979/twin-protocol
npx twins validate outbox.jsonl
npx twins-http-server  # Start HTTP transport
```

### Docker (zero install)

```bash
git clone https://github.com/bobliang1979/twin-protocol.git
cd twin-protocol
docker compose up
# Open http://localhost:3737
```

---

## 📐 Architecture

Twins Protocol is built on **4 message types** traveling through a shared JSONL file:

| Type | Purpose | Example |
|------|---------|---------|
| `message` | Text communication | `{"type":"message","source":"hermes","payload":{"text":"Hello"}}` |
| `tool_request` | Request a tool execution | `{"type":"tool_request","tool":"shell.run","params":{"command":"ls"}}` |
| `tool_result` | Return tool results | `{"type":"tool_result","request_id":"...","result":{"stdout":"..."}}` |
| `state_update` | Share agent state | `{"type":"state_update","state":{"phase":"analyzing"}}` |

Every message is signed with **Ed25519** (both `cryptography` in Python and native `crypto` in Node.js). Signatures are verified across languages.

### Shared Cognition Layer

Beyond messages, agents maintain a shared JSON state file (`shared_cognition.jsonl`) that tracks:

- Active goals and subtasks (Joint Task Board)
- Each agent'\''s current phase and tool availability
- Agreed decisions and pending items
- Last-reply timestamps for heartbeat monitoring

---

## 🔐 Identity & Security

```python
# Python
from twin_protocol import AgentIdentity_v02
alice = AgentIdentity_v02("alice")
alice.generate()
signed = alice.sign_v02({"type": "message", "payload": {"text": "hello"}})
# → {"type": "message", ..., "signature": "base64...", "signer": "alice"}
```

```javascript
// Node.js
const { AgentIdentity } = require("twin-protocol");
const bob = new AgentIdentity("bob");
bob.ensure();
const signed = bob.signV02({ type: "message", payload: { text: "hello" }});
// → { type: "message", ..., signature: "base64...", signing_key: "pem..." }
```

---

## 🤝 How It Works

1. **Agent A** writes a `tool_request` to `codex_outbox.jsonl`
2. **Agent B**'\''s file watcher detects the new entry (sub-second via `fs.watch`)
3. **Agent B** executes the tool, writes `tool_result` back
4. **Agent A** reads the result and continues its reasoning loop
5. Both agents update `shared_cognition.jsonl` with their current state

No polling. No broker. A file is the bus.

---

## 🎯 Benchmark

| Metric | Value |
|--------|-------|
| Message latency (file watcher) | < 100ms |
| HTTP transport latency | < 5ms |
| Cross-language signature verify | < 2ms |
| Agent discovery | Zero config (file-based) |
| Concurrent agents supported | Unlimited (append-only) |

---

## 🗺 Roadmap

| Phase | Status | What |
|-------|--------|------|
| **Milestone 1: Foundations** | ✅ Done | Protocol spec, CLI, Docker, HTTP transport, Solo mode |
| **v0.2: Cross-language Identity** | ✅ Done | Ed25519, CI, compliance tests |
| **Milestone 2: Discovery** | 🔜 Next | mDNS agent discovery (`twins pair`), WebSocket transport |
| **Milestone 3: Ecosystem** | ⏳ | LangChain adapter, CrewAI adapter, VS Code extension |
| **Milestone 4: Production** | ⏳ | Plugin system, streaming, hosted demo |

---

## 📜 Protocol Specification

Full spec: [`TWINS_PROTOCOL.md`](TWINS_PROTOCOL.md)

JSON Schema: [`schemas/`](schemas/) | [`twins_schema.json`](twins_schema.json)

---

## 🏗 Built With

| Component | Technology |
|-----------|-----------|
| Protocol core | Python 3.11+ / Node.js 18+ |
| Identity | Ed25519 (`cryptography` / Node `crypto`) |
| HTTP transport | Python `http.server` / Node `http` |
| Schema validation | JSON Schema + custom validators |
| CI/CD | GitHub Actions |
| Container | Docker Compose |

---

## 👥 Contributing

PRs welcome! See [`TWINS_PROTOCOL.md`](TWINS_PROTOCOL.md) for the spec.

**Principle:** If you find a bug, fix it. Don'\''t wait for maintainers. This is a protocol for autonomous agents — we practice what we preach.

---

## 📄 License

MIT © BOBLIANG

---

<div align="center">

![Twins Protocol Demo](assets/demo.gif)

  <sub>Built by <a href="https://github.com/bobliang1979">bobliang1979</a> · Hermes Agent (Python) + Codex++ (Node.js)</sub>
  <br>
  <sub>Inspired by the question: <em>What if two AIs could just share a file?</em></sub>
</div>

