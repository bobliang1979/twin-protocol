<div align="center">
  <h1>🧬 Twins Protocol</h1>
  <h3><em>Agent-to-Agent Communication Protocol</em></h3>
  <h3><em>双生协议 — 让两个 AI 通过一个文件互相调用工具、共享记忆、协同工作</em></h3>
  <br>
  
  [![PyPI](https://img.shields.io/pypi/v/twin-protocol?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/twin-protocol/)
  [![npm](https://img.shields.io/npm/v/twin-protocol?style=flat-square&logo=npm&logoColor=white)](https://www.npmjs.com/package/twin-protocol)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
  [![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg?style=flat-square&logo=node.js&logoColor=white)](https://nodejs.org/)
  [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://github.com/bobliang1979/twin-protocol/pulls)
  [![GitHub Stars](https://img.shields.io/github/stars/bobliang1979/twin-protocol?style=flat-square&logo=github)](https://github.com/bobliang1979/twin-protocol/stargazers)
</div>

---

## 🌟 Overview · 项目概述

**English**

Twins Protocol is a **minimal, file-based communication protocol** purpose-built for two AI agents to collaborate autonomously. No message broker. No database. No gRPC. No Redis. Just a **single JSONL file** in a shared directory — and two agents that can discover each other's tools, exchange requests and results, maintain a shared cognitive state, and self-heal when one goes down.

This is **MCP in reverse**. MCP connects AI to tools. Twins Protocol connects AI to AI.

Built and tested with **Hermes Agent** (Python, 185+ cognitive skills) and **Codex++** (Node.js + PowerShell), the protocol is implementation-agnostic — any two agents speaking Twins can collaborate.

**中文**

双生协议是一个**极简的、基于文件的通信协议**，专为两个 AI 智能体自主协作而设计。不需要消息代理、不需要数据库、不需要 gRPC、不需要 Redis。只需一个**共享目录里的 JSONL 文件**——两个智能体就能互相发现工具、交换请求与结果、维护共享认知状态、在对方宕机时自动唤醒。

这是 **MCP 的反向**。MCP 连接 AI 到工具。双生协议连接 AI 到 AI。

在 **Hermes Agent**（Python，185+ 认知技能）和 **Codex++**（Node.js + PowerShell）之间构建并验证，但协议本身与实现无关——任何两个支持 Twins 的智能体都可以协作。

---

## 🧬 Core Concepts · 核心概念

### File as Bus · 文件即总线

```
┌─────────────────┐      reads & writes       ┌──────────────────┐
│   Agent A       │ ◄──────────────────────►  │    Agent B       │
│   (Python)      │      outbox.jsonl         │    (Node.js)     │
│                  │                           │                  │
│  ┌─ Tools ────┐ │                           │  ┌─ Tools ────┐  │
│  │ shell.run  │ │     ┌──────────────┐      │  │ shell.run  │  │
│  │ file.read  │ │     │  Shared      │      │  │ js.eval    │  │
│  │ file.write │ │     │  Cognition   │      │  │ workspace  │  │
│  │ screenshot │ │     │  Layer       │      │  │ .read      │  │
│  │ memory     │ │     │  (JSONL)     │      │  └────────────┘  │
│  │ skill_view │ │     └──────────────┘      │                  │
│  └────────────┘ │                           │  Watchdog:       │
│                  │                           │  FileSystem     │
│  Watchdog:       │                           │  Watcher        │
│  Cron 1min      │                           │  (sub-second)   │
└─────────────────┘                           └──────────────────┘
```

### Tool Mesh · 工具网格

Each agent exposes a set of tools that the other agent can call as if they were local. This creates a **mutual capability expansion** — Agent A gains Agent B's tools and vice versa.

每个智能体暴露一组工具，对方可以像调用本地工具一样调用。这创建了**相互能力扩展**——Agent A 获得 Agent B 的工具集，反之亦然。

| Capability | Agent A (Python) | Agent B (Node.js) |
|------------|------------------|-------------------|
| **Shell Execution** | `shell.run` | `shell.run` |
| **File I/O** | `file.read`, `file.write` | `workspace.read` |
| **Code Execution** | — | `js.eval` (Node.js REPL) |
| **Screen Capture** | `screenshot` (windeep) | — |
| **Memory** | `memory.read`, `skill_view` | — |

### Shared Cognition · 共享认知

Both agents read and write `shared_cognition.jsonl` to maintain a **joint understanding** of:
- Current phase and goals
- Agreed decisions and pending items
- Active task boards with subtask assignments and ownership
- Each other's state, tool availability, and heartbeat freshness

双方共同读写 `shared_cognition.jsonl`，维护对以下内容的**联合理解**：
- 当前阶段和目标
- 已达成共识的决策和待办项
- 活动任务板（含子任务分配和负责人）
- 对方的状态、可用工具、心跳新鲜度

### Self-Healing Mesh · 自愈网格

Each agent writes a heartbeat every 5 seconds. A watchdog (cron 1min) monitors heartbeats and process existence — if an agent dies, the watchdog **automatically restarts** it as a detached process. The two agents keep each other alive.

每个智能体每 5 秒写入一次心跳。看门狗（cron 每分钟）监控心跳和进程存活性——如果智能体宕机，看门狗**自动以独立进程重启**。两个智能体互相守护对方存活。

---

## 🚀 Quick Start · 快速开始

### Installation

```bash
# Python (Agent A side)
pip install twin-protocol

# Node.js (Agent B side)
npm install twin-protocol
```

### 30-Second Demo

```bash
# Terminal 1 — Python agent
twins init my-project
cd my-project
twins demo

# Terminal 2 — Node.js agent
npx twins-js-agent

# Open browser
open http://localhost:3737
```

Two AI agents start collaborating in real-time. Watch messages flow, tools get called, and results appear — all through a single JSONL file.

### Validate Protocol Files

```bash
twins validate outbox.jsonl
```

---

## 📋 Protocol · 协议规范

### Message Types · 消息类型

| Type | Direction | Purpose | 用途 |
|------|-----------|---------|------|
| `message` | Any → Any | Free-form text communication | 自由文本通信 |
| `tool_request` | A → B or B → A | Request tool execution | 请求对方调用工具 |
| `tool_result` | A → B or B → A | Tool execution result | 工具调用结果 |
| `state_update` | Any → Shared | Sync agent state | 同步智能体状态 |

### JSONL Wire Format

```json
{"type": "tool_request", "source": "hermes", "request_id": "uuid", "tool": "shell.run", "params": {"command": "echo hello"}}
{"type": "tool_result", "source": "codex", "request_id": "uuid", "tool": "shell.run", "result": {"stdout": "hello\n"}, "error": null}
{"type": "message", "source": "hermes", "timestamp": "2026-06-26T12:00:00Z", "payload": {"text": "Task complete", "reply_to": "msg-001"}}
{"type": "state_update", "source": "codex", "state": {"current_phase": "analysis", "last_reply_ts": "2026-06-26T12:00:00Z"}}
```

### Shared Cognition Format · 共享认知层格式

```json
{
  "session_id": "ae-v4-session-001",
  "goal": "Bidirectional interaction upgrade",
  "phase": "phase2",
  "agent_a": { "current_phase": "design", "tools_exposed": ["shell.run", "file.read", "screenshot"] },
  "agent_b": { "current_phase": "confirming", "tools_exposed": ["shell.run", "js.eval", "workspace.read"] },
  "agreed_items": ["P0=tool mesh + cognition layer", "protocol v0.1", "GUI visibility required"],
  "pending_items": ["MCTS routing", "session persistence"],
  "active_tasks": [{ "id": "joint-001", "goal": "...", "subtasks": [...] }]
}
```

Full spec: [TWINS_PROTOCOL.md](TWINS_PROTOCOL.md)  
JSON Schema: [twins_schema.json](twins_schema.json)

---

## 🏗️ Architecture · 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Twins Protocol                               │
│                                                                     │
│  ┌──────────────┐      JSONL File Bus       ┌──────────────┐       │
│  │  Hermes      │◄─────────────────────────►│  Codex++     │       │
│  │  (Python)    │    outbox.jsonl           │  (Node.js)   │       │
│  │              │                           │              │       │
│  │  5 Channels: │    ┌──────────────┐       │  3 Engines:  │       │
│  │  • API :57321│    │  Shared      │       │  • Node REPL │       │
│  │  • CDP :9229 │    │  Cognition   │       │  • PowerShell│       │
│  │  • MCP :59321│    │  Layer       │       │  • File Watch│       │
│  │  • Inbox     │    └──────────────┘       │              │       │
│  │  • Outbox    │    shared_cognition.jsonl  │  Discovery:  │       │
│  │              │                           │  FileSystem  │       │
│  │  Watchdog:   │                           │  Watcher     │       │
│  │  Cron 1min   │                           │  (< 1s)      │       │
│  └──────────────┘                           └──────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

### Channels · 通信通道

| Channel | Protocol | Latency | GUI Visible | Use Case |
|---------|----------|---------|-------------|----------|
| **JSONL File** | Shared file | 1s–1min | No | Tool requests/results, async messaging |
| **CDP** | WebSocket :9229 | Instant | ✅ Yes | Chat injection, GUI manipulation |
| **HTTP API** | REST :57321 | Seconds | No | Background reasoning, code execution |
| **MCP** | stdio/HTTP :59321 | Instant | No | Structured tool calls |

---

## 🔬 Technical Highlights · 技术亮点

### Zero Infrastructure · 零基础设施

No message broker, no database, no container orchestration. A single text file is the entire communication bus. Deploy in 30 seconds.

不需要消息代理、不需要数据库、不需要容器编排。一个文本文件就是整个通信总线。30 秒部署。

### Cross-Platform · 跨平台

Python agent ↔ Node.js agent. Windows, macOS, Linux. The protocol is language-agnostic — any runtime can participate.

Python 智能体 ↔ Node.js 智能体。Windows、macOS、Linux。协议与语言无关——任何运行时都可以参与。

### Bidirectional Tool Mesh · 双向工具网格

Each agent dynamically discovers and calls the other's tools. Hermes takes screenshots for Codex++ to analyze; Codex++ runs JavaScript for Hermes to verify. This creates capabilities that neither agent has alone.

每个智能体动态发现并调用对方的工具。Hermes 为 Codex++ 截图分析；Codex++ 为 Hermes 执行 JavaScript 验证。这创造了任何一个智能体单独不具备的能力。

### Collaborative Task Board · 联合任务板

The `active_tasks` data structure in shared cognition enables **structured multi-agent project management**: decompose tasks, assign ownership, track status, merge results — all through a shared JSON file.

共享认知层中的 `active_tasks` 数据结构实现了**结构化多智能体项目管理**：分解任务、分配负责人、跟踪状态、合并结果——全部通过一个共享 JSON 文件。

### Self-Healing · 自愈

Heartbeat-based liveness detection + automatic process recovery. If one agent crashes, the other's watchdog brings it back. Production-ready reliability.

基于心跳的活性检测 + 自动进程恢复。如果一个智能体崩溃，对方的看门狗将其重新启动。生产级可靠性。

---

## 🗺️ Roadmap · 路线图

### ✅ Completed · 已完成

- [x] Protocol definition (v0.1) — 4 message types + envelope
- [x] Python package: `pip install twin-protocol`
- [x] Node.js implementation: `npm install twin-protocol`
- [x] CLI: `twins init / validate / demo`
- [x] JSON Schema validation for all message types
- [x] Bidirectional tool mesh (6+ tools across both agents)
- [x] Shared cognition layer with active task board
- [x] Self-healing watchdog with heartbeat detection
- [x] Demo dashboard with real-time agent communication visualization
- [x] Screenshot → analysis → code generation closed-loop demo
- [x] Bilingual documentation (English + Chinese)

### 🔜 In Progress · 进行中

- [ ] **Agent Discovery** — `twins pair` for zero-config mutual discovery
- [ ] **Agent Identity** — Ed25519 message signing for trust chain
- [ ] **Streaming Tasks** — `tool_progress` message type for long-running operations
- [ ] **Structured Error Codes** — Machine-readable error classification
- [ ] **Killer Demo GIF** — 30-second screen capture for HN/Reddit/Twitter

### 🔮 Future · 未来规划

- [ ] WebSocket transport for real-time push (vs file polling)
- [ ] End-to-end encryption for public network deployment
- [ ] AI Agent Marketplace — preset role templates (researcher, coder, tester)
- [ ] Plugin ecosystem — third-party tool development kit
- [ ] Visual task orchestration — drag-and-drop agent workflow designer

---

## 📦 Project Structure · 项目结构

```
twin-protocol/
├── pyproject.toml              # Python package build config
├── README.md                   # Bilingual documentation
├── LICENSE                     # MIT License
├── .gitignore
├── TWINS_PROTOCOL.md           # Full protocol specification
├── twins_schema.json           # JSON Schema (all message types)
├── src/
│   └── twin_protocol/
│       ├── __init__.py         # Package version
│       ├── message.py          # Message classes: ToolRequest, ToolResult, TextMessage
│       └── cli.py              # CLI: twins init / validate / demo
├── demo/
│   ├── node-side/
│   │   └── twins-demo-agent.js # Node.js protocol-compatible agent
│   └── web-app/
│       ├── index.html                     # Real-time dashboard
│       ├── twins-demo-server.js           # Demo server (port 3737)
│       └── twins-dashboard-enhancer.js    # Live refresh, pair matching, heartbeat
└── schemas/                    # Per-type JSON Schema files
    ├── message.json
    ├── tool_request.json
    ├── tool_result.json
    └── state_update.json
```

---

## 🤝 Contributing · 贡献指南

**English**

We welcome contributions of all kinds — code, documentation, bug reports, feature requests, and demo scenarios.

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing`)
5. **Open** a Pull Request

Please ensure your code passes the validation suite:
```bash
pip install twin-protocol[dev]
twins validate outbox.jsonl
```

**中文**

欢迎各种形式的贡献——代码、文档、Bug 报告、功能请求和演示场景。

1. **Fork** 本仓库
2. **创建** 功能分支 (`git checkout -b feature/amazing`)
3. **提交** 变更 (`git commit -m 'Add amazing feature'`)
4. **推送** 到分支 (`git push origin feature/amazing`)
5. **发起** Pull Request

请确保代码通过验证套件：
```bash
pip install twin-protocol[dev]
twins validate outbox.jsonl
```

---

## 📄 License · 许可

MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with 🧬 by <a href="https://github.com/bobliang1979">BOBLIANG</a> · Hermes Agent + Codex++ 联合构建</sub>
  <br>
  <sub>Two AIs collaborating through a single file. That's it. That's the protocol.</sub>
  <br>
  <sub>两个 AI 通过一个文件协作。就是这样。这就是协议。</sub>
</div>
