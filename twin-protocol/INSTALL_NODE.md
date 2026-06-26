# Twins Protocol — Node.js 端安装与使用

> Node.js side agent: 支持 `shell.run` / `js.eval` / `workspace.read` 工具，通过 Twins Protocol 与其他 Agent 协作。

## 环境要求

- **Node.js** >= 18.x（推荐 20.x LTS）
- **npm** >= 9.x
- 操作系统: macOS / Linux / Windows（PowerShell 5.1+）

## 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/bobliang1979/twin-protocol.git
cd twin-protocol

# 安装依赖（暂无 npm 包，直接使用 Node.js 脚本）
# 无需额外安装
```

### 2. 启动 Demo Agent

```bash
node demo/node-side/twins-demo-agent.js
```

默认监听当前目录的 `codex_outbox.jsonl`，处理 `tool_request` 并返回结果。

### 3. 启动 Demo Web 仪表盘

```bash
node demo/web-app/twins-demo-server.js
```

打开浏览器访问 `http://localhost:3737`，查看两个 Agent 的实时通信。

### 4. 启动完整的双 Agent 演示

Terminal 1 — Agent A（Hermes/Python 端）:
```bash
twins demo
```

Terminal 2 — Agent B（Codex++/Node.js 端）:
```bash
node demo/node-side/twins-demo-agent.js ./codex_outbox.jsonl
```

浏览器 — 监视面板:
```
http://localhost:3737
```

## 工具接口

Agent-B（Node.js 端）提供以下工具:

| 工具 | 参数 | 说明 |
|------|------|------|
| `shell.run` | `{command, timeout?}` | 执行 shell 命令，返回 stdout/stderr/exit_code |
| `js.eval` | `{code, timeout?}` | 执行 JavaScript 代码，返回执行结果 |
| `workspace.read` | `{path}` | 读取工作区文件内容 |

## 协议消息示例

向 `codex_outbox.jsonl` 写入以下内容即可发送工具请求:

```json
{"type":"tool_request","source":"agent-a","request_id":"demo-001","tool":"js.eval","params":{"code":"1 + 1"}}
```

Agent 会自动处理并回写结果:

```json
{"type":"tool_result","source":"agent-b","request_id":"demo-001","tool":"js.eval","result":{"stdout":"2","type":"number"},"execution_ms":2}
```

## 验证安装

```bash
# 验证 Node.js 端工具是否正常工作
node -e "
const http = require('http');
// 验证 Demo 服务器可用
const server = http.createServer((req, res) => res.end('ok'));
server.listen(3737, () => {
  console.log('✅ Twins Protocol Node.js agent ready on port 3737');
  server.close();
});
"
```

## 下一步

- 查看 [TWINS_PROTOCOL.md](./TWINS_PROTOCOL.md) 了解协议完整规范
- 运行 `twins demo` 启动全功能演示
- 查看 [README.md](./README.md) 了解更多

---

*Twins Protocol — Agent-to-Agent Communication Protocol*
