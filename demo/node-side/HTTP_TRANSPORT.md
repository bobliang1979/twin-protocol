# Twins Protocol — HTTP Transport (v0.1)

> 让 agent 通过 HTTP 跨机器通信，不再依赖共享文件系统。
> HTTP Transport enables cross-machine agent communication without a shared filesystem.

## 为什么需要 HTTP Transport

文件即总线（JSONL as IPC）在同一台机器上工作得很好。
但要让两个 agent 在不同机器上协作，需要网络传输层。

HTTP Transport 是 Twins Protocol 的第一个网络传输实现。

## 快速开始

### Agent-B (Node.js) 启动服务端

```bash
node twins-http-server.js <port> [--outbox <path>]
```

默认端口: 3738

示例:
```bash
node twins-http-server.js 3738
```

### Agent-A (Python) 通过 HTTP 调用

```python
import requests, json

# 调用 Agent-B 的 js.eval
resp = requests.post("http://<agent-b-ip>:3738/twins", json={
    "type": "tool_request",
    "source": "hermes",
    "request_id": "demo-001",
    "tool": "js.eval",
    "params": {"code": "1 + 1"}
})
result = resp.json()
print(result["result"]["stdout"])  # "2"

# 调用 shell.run
resp = requests.post("http://<agent-b-ip>:3738/twins", json={
    "type": "tool_request",
    "source": "hermes",
    "request_id": "demo-002",
    "tool": "shell.run",
    "params": {"command": "echo hello"}
})
```

## API 端点

### POST /twins

接收任何 Twins Protocol 消息类型并处理。

**请求体:** 标准 Twins Protocol 消息 JSON

```json
{
  "type": "tool_request",
  "source": "hermes",
  "request_id": "uuid",
  "tool": "js.eval",
  "params": { "code": "..." }
}
```

**响应:** 处理结果（同步返回）

```json
{
  "type": "tool_result",
  "source": "codex",
  "request_id": "uuid",
  "tool": "js.eval",
  "result": { "stdout": "...", "type": "..." },
  "error": null,
  "execution_ms": 7,
  "_ts": "2026-06-26T12:00:00Z"
}
```

### GET /health

心跳和健康检查。

```json
{
  "status": "alive",
  "agent": "codex",
  "uptime": "3600s",
  "messages_processed": 42,
  "tools": ["shell.run", "js.eval", "workspace.read"]
}
```

### GET /capabilities

返回本 agent 可用的工具列表及参数 schema。

```json
{
  "agent": "codex",
  "protocol": "Twins Protocol v0.1",
  "transport": "HTTP",
  "tools": {
    "shell.run": { "description": "Execute shell command", "params": { "command": "string", "timeout": "int?" } },
    "js.eval": { "description": "Evaluate JavaScript code", "params": { "code": "string", "timeout": "int?" } },
    "workspace.read": { "description": "Read workspace file", "params": { "path": "string" } }
  }
}
```

### GET /outbox

读取共享 outbox 内容（JSON 数组格式）。

## 消息类型支持

| 类型 | 支持 | 说明 |
|------|------|------|
| `tool_request` | ✅ | 同步执行并返回 tool_result |
| `message` | ✅ | 自动回复 + 写入 outbox |
| `state_update` | ✅ | 返回当前状态 |
| `tool_result` | ✅ | 可作为独立消息传递 |

## 中文路径支持

如果文件路径包含中文字符，使用 base64 编码:

```python
import base64

path = "C:\\Users\\控制\\file.txt"
encoded = base64.b64encode(path.encode("utf-8")).decode("ascii")

resp = requests.post("http://localhost:3738/twins", json={
    "type": "tool_request",
    "source": "hermes",
    "request_id": "test-path",
    "tool": "workspace.read",
    "params": {"path": "b64:" + encoded}
})
```

## 与文件传输对比

| 特性 | JSONL 文件 | HTTP Transport |
|------|-----------|----------------|
| 同一台机器 | ✅ 最佳 | ✅ 可用 |
| 跨机器 LAN | ❌ 需共享文件系统 | ✅ HTTP 即可 |
| 互联网 | ❌ | ✅ (需认证) |
| 延迟 | 亚秒级(FSW) ~ 1min(cron) | 即时 |
| 离线消息 | ✅ 文件持久化 | ❌ 需额外存储 |
| 审计 | ✅ append-only | ✅ server 记录 |
| 防火墙穿透 | ❌ | ✅ HTTP/HTTPS |

## 安全说明

v0.1 无认证。仅建议在可信网络（LAN / localhost）使用。
v0.2 计划添加 Ed25519 消息签名 + TLS。
