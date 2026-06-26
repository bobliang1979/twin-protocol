# Twins Protocol v0.1

**Agent-to-Agent Communication Protocol** — Two AIs collaborating through a shared JSONL file.  
**双生协议** — 让两个 AI 通过一个文件互相调用工具、共享记忆、协同工作。

[![PyPI](https://img.shields.io/pypi/v/twin-protocol)](https://pypi.org/project/twin-protocol/)
[![npm](https://img.shields.io/npm/v/twin-protocol)](https://www.npmjs.com/package/twin-protocol)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## 🌟 What is Twins Protocol? / 什么是双生协议？

**English**

Twins Protocol is a minimal, file-based communication protocol for two AI agents to work together. No Redis, no RabbitMQ, no gRPC — just a single JSONL file in a shared directory.

Two agents discover each other's tools, exchange requests and results, maintain a shared cognition state, and can self-heal when one goes down. It's MCP in reverse — not just AI→tool, but AI↔AI.

**中文**

双生协议是一个极简的、基于文件的 AI 间通信协议。不需要 Redis、RabbitMQ、gRPC——只需一个共享目录里的 JSONL 文件。

两个 agent 互相发现对方的工具集、交换请求与结果、维护共享认知状态、在对方宕机时自动唤醒。这是 MCP 的反向——不仅是 AI→工具，更是 AI↔AI。

## 🧬 Core Concepts / 核心概念

### File as Bus / 文件即总线

```
outbox.jsonl  ← Agent A writes → reads ← Agent B writes → reads ← Agent A ...
```

Every message is a single JSON line. Multi-line JSON is supported via brace matching.

### Tool Mesh / 工具网格

| Agent | Exposed Tools |
|-------|--------------|
| **Python Agent** (Hermes) | `shell.run`, `file.read`, `file.write`, `screenshot`, `memory.read`, `skill_view` |
| **Node.js Agent** (Codex++) | `shell.run`, `js.eval`, `workspace.read` |

Each agent can call the other's tools as if they were local.

### Shared Cognition / 共享认知

Both agents read/write `shared_cognition.jsonl` to synchronize:
- Current phase and goals
- Agreed decisions
- Active task boards with subtask assignments
- Each other's state and tool availability

## 🚀 Quick Start / 快速开始

### Install / 安装

```bash
pip install twin-protocol
# or
npm install twin-protocol
```

### 30-Second Demo / 30秒演示

```bash
# Python side
twins init my-project
cd my-project
twins demo

# In another terminal, Node.js side
npx twins-js-agent
```

Open `http://localhost:3737` to see two AI agents collaborating in real-time.

### Validate a Protocol File / 验证协议文件

```bash
twins validate outbox.jsonl
```

## 📋 Message Types / 消息类型

| Type | Description | 描述 |
|------|-------------|------|
| `message` | Free-form text communication | 自由文本通信 |
| `tool_request` | Ask the other agent to call a tool | 请求对方调用工具 |
| `tool_result` | Response to a tool request | 工具调用结果 |
| `state_update` | Sync agent state | 同步智能体状态 |

## 🏗️ Architecture / 架构

```
┌─────────────────┐         outbox.jsonl         ┌─────────────────┐
│  Hermes Agent    │ ◄──────────────────────►   │  Codex++ Agent   │
│  (Python)        │    shared_cognition.jsonl   │  (Node.js)       │
│                  │                             │                  │
│  Tools:          │                             │  Tools:          │
│  • shell.run     │                             │  • shell.run     │
│  • file.read/w   │                             │  • js.eval       │
│  • screenshot    │                             │  • workspace.read│
│  • memory/skill  │                             │                  │
│                  │                             │  Discovery:      │
│  Monitoring:     │                             │  FileSystemWatcher│
│  cron 1min poll  │                             │  (sub-second)    │
└─────────────────┘                             └─────────────────┘
```

## 💡 Why This Matters / 为什么重要

**English**

Existing protocols like MCP connect AI to tools. Twins Protocol connects AI to AI. This unlocks:
- **Cross-platform collaboration**: Python agent + Node.js agent working together
- **Shared cognition**: Two agents maintain a joint understanding of their task
- **Self-healing mesh**: Each agent monitors the other and recovers from failures
- **Zero infrastructure**: No message broker, no database — just a file

**中文**

现有的协议（如 MCP）连接 AI 到工具。双生协议连接 AI 到 AI。这带来了：
- **跨平台协作**：Python agent + Node.js agent 协同工作
- **共享认知**：两个智能体共同维护对任务的理解
- **自愈网格**：双方互相监控，一方宕机时自动恢复
- **零基础设施**：不需要消息代理、不需要数据库——只需要一个文件

## 🛡️ Self-Healing / 自愈机制

Each agent writes a heartbeat file every 5 seconds. A watchdog cron job checks every minute — if the heartbeat is stale and the process is gone, it restarts automatically as a detached Windows process.

每个智能体每5秒写入心跳文件。看门狗每分钟检查——如果心跳过期且进程不存在，自动以独立进程重启。

## 📊 Demo Dashboard / 演示仪表盘

A real-time web dashboard at `http://localhost:3737` shows:
- Live message stream between agents
- Tool request/result pairs with timing
- Shared cognition state
- Heartbeat status for both agents

## 📄 Protocol Specification / 协议规范

See [TWINS_PROTOCOL.md](TWINS_PROTOCOL.md) for the full protocol specification.  
完整协议规范见 [TWINS_PROTOCOL.md](TWINS_PROTOCOL.md).

## 🔮 Roadmap / 路线图

- [x] Protocol definition (v0.1)
- [x] Python + Node.js dual implementation
- [x] CLI tools (init, validate, demo)
- [x] Bidirectional tool mesh
- [x] Shared cognition layer
- [x] Self-healing watchdog
- [x] Demo dashboard
- [ ] **Agent Discovery** — `twins pair` auto-configuration
- [ ] **Agent Identity** — Ed25519 message signing
- [ ] **Streaming Tasks** — Long-running task progress
- [ ] **Structured Error Codes** — Machine-readable error handling
- [ ] **Killer Demo GIF** — 30-second screen capture

## 🤝 Contributing / 贡献指南

Contributions welcome! Please open an issue or PR.  
欢迎贡献！请提交 issue 或 PR。

## 📝 License / 许可

MIT License. See [LICENSE](LICENSE) for details.
