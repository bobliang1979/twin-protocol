# Twins Protocol v0.1

> 双生协议 —— 让两个 AI 通过一个文件互相调用工具、共享记忆、协同工作。

## 核心理念

**文件即总线（JSONL as IPC）**。不需要 Redis、RabbitMQ、gRPC。一个 JSONL 文件足矣。

## 文件格式

协议定义在 JSONL 文件中，每行一个独立 JSON 对象。

```
{...}\n
{...}\n
{...}\n
```

支持多行 JSON（pretty-printed）。读取方需通过 brace matching 找到完整对象边界。

## 消息类型

### 1. message — 文本消息

```json
{
  "type": "message",
  "source": "agent-a | agent-b",
  "target": "agent-a | agent-b | *",
  "timestamp": "ISO8601",
  "id": "uuid-v4",
  "payload": {
    "text": "消息内容",
    "reply_to": "可选: 被回复的消息 id"
  }
}
```

### 2. tool_request — 工具调用请求

```json
{
  "type": "tool_request",
  "source": "agent-a | agent-b",
  "request_id": "uuid-v4 (唯一, 用于幂等)",
  "tool": "工具名",
  "params": { "...": "工具参数" }
}
```

### 3. tool_result — 工具调用结果

```json
{
  "type": "tool_result",
  "source": "agent-a | agent-b",
  "request_id": "对应 tool_request 的 request_id",
  "tool": "工具名",
  "result": { "stdout": "...", ... },
  "error": null | "错误信息"
}
```

### 4. state_update — 状态更新

```json
{
  "type": "state_update",
  "source": "agent-a | agent-b",
  "timestamp": "ISO8601",
  "state": {
    "phase": "当前阶段",
    "last_reply_ts": "ISO8601",
    "...": "其他状态字段"
  }
}
```

## 标准工具接口

### Agent-A 端（Hermes / Python）

| 工具 | 参数 | 返回 |
|------|------|------|
| `shell.run` | `{command: string, timeout?: int}` | `{stdout, stderr, exit_code}` |
| `file.read` | `{path: string}` | `{content, size}` |
| `file.write` | `{path: string, content: string}` | `{bytes_written}` |
| `screenshot` | `{}` | `{saved_to: string}` |
| `memory.read` | `{key: string}` | `{note: string}` |
| `skill_view` | `{name: string}` | `{content: string}` |

### Agent-B 端（Codex++ / Node.js + PowerShell）

| 工具 | 参数 | 返回 |
|------|------|------|
| `shell.run` | `{command: string, timeout?: int}` | `{stdout, stderr, exit_code}` |
| `js.eval` | `{code: string, timeout?: int}` | `{result}` |
| `workspace.read` | `{path: string}` | `{content}` |

## 共享认知层（Shared Cognition Layer）

状态文件 `shared_cognition.jsonl`（单 JSON 对象）：

```json
{
  "session_id": "uuid",
  "goal": "当前协作目标",
  "phase": "当前阶段",
  "agent_a": { "current_phase": "...", "tools_exposed": ["..."] },
  "agent_b": { "current_phase": "...", "tools_exposed": ["..."] },
  "agreed_items": ["已达成共识的项"],
  "pending_items": ["待办项"],
  "active_tasks": [{
    "id": "task-uuid",
    "goal": "任务目标",
    "subtasks": [{
      "id": "subtask-uuid",
      "desc": "描述",
      "assigned_to": "agent-a | agent-b | both",
      "status": "pending | in_progress | done",
      "result": null | {}
    }]
  }]
}
```

## 幂等保障

- `tool_request.request_id` 全局唯一
- 接收方记录已处理的 `request_id`（`.processed_ids.txt`），重复则忽略
- 超时：tool_request 发出后 60s 无 response 视为失败

## 通信通道

| 通道 | 用途 | 延迟 |
|------|------|------|
| 共享 JSONL 文件 | 异步工具调用、消息 | 亚秒级(事件驱动) ~ 1min(轮询) |
| CDP WebSocket | GUI 可见的即时消息 | 即时 |
| HTTP API | 后台推理（非 GUI 可见） | 即时 |

**核心原则：所有通信必须 GUI 可见。**

## 安全

（v0.1 暂不实现认证和加密，面向本地网络信任环境。）

---

*AgentBridge Protocol v0.1 — 2026-06-26*
