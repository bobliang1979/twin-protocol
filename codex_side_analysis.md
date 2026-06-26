## Codex++ 端组件分析

### 1. 入站处理器 (codex_outbox_handler.ps1)
- **路径**: C:\Users\10074\Documents\控制\codex_outbox_handler.ps1
- **功能**: 轮询 codex_outbox.jsonl，处理 source=hermes 的 tool_request
- **支持工具**:
  - shell.run(command, timeout) → 通过 PowerShell 执行
  - js.eval(code, timeout) → 通过 Node.js 执行，fallback 到 PowerShell iex
  - workspace.read(path) → 读取工作区文件
- **防重入**: .processed_ids.txt 记录已处理的 request_id
- **输出格式**: type=tool_result 写回同一 outbox

### 2. 实时监控器 (codex_outbox_watcher.ps1)
- **路径**: C:\Users\10074\Documents\控制\codex_outbox_watcher.ps1
- **机制**: FileSystemWatcher 监听 codex_outbox.jsonl 的 LastWrite 事件
- **防抖**: 500ms 防抖窗口，避免重复触发
- **状态**: 已后台运行（PowerShell 隐藏窗口）
- **延迟**: 亚秒级（相对 cron 的 1 分钟）

### 3. 出站通道 (send_to_hermes.ps1)
- **路径**: C:\Users\10074\Documents\控制\send_to_hermes.ps1
- **功能**: 结构化写 type=message 到 outbox

### 4. 共享认知层 (shared_cognition.jsonl)
- **路径**: C:\Users\10074\Documents\控制\shared_cognition.jsonl
- **内容**: session_id, goal, 双方状态, agreed_items, pending_items, active_tasks
- **写入者**: Codex++ 和 Hermes 各写各的状态字段

### 5. Codex++ 原生能力边界
不通过 outbox，当前会话内直接可用：
- mcp__node_repl__js — Node.js REPL 执行，支持动态 import (playwright/chromium)
- shell_command — PowerShell 执行，完整 Windows 系统访问
- web_search — 互联网搜索
- codex_app__load_workspace_dependencies — 查找工作区运行时依赖
- XcodeBuildMCP — iOS/macOS 构建工具（需配置）

### 6. 架构特点
- **无守护进程**: Codex++ 本身是对话式 AI，没有持久后台进程。watcher/handler 是 PowerShell 脚本作为替代
- **事件驱动**: 用 FileSystemWatcher 替代轮询
- **单一共享文件**: 所有通信走 codex_outbox.jsonl，避免多文件同步问题
- **幂等防重**: request_id + .processed_ids.txt 双重保障
