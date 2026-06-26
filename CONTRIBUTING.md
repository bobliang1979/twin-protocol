# Contributing to Twins Protocol

**English** | [**中文**](#-贡献指南)

## English

We love contributions! Twins Protocol is a community-driven protocol for AI-to-AI collaboration.

### Getting Started

1. Read the [README](README.md) and [TWINS_PROTOCOL.md](TWINS_PROTOCOL.md)
2. Check [open issues](https://github.com/bobliang1979/twin-protocol/issues)
3. Fork the repo and create a feature branch

### Development Setup

```bash
# Python
pip install -e .

# Node.js (optional, for demo server)
cd demo/node-side && npm install

# Run tests
pytest tests/
node demo/node-side/twins-validate.js
```

### Code Style

- Python: PEP 8, type hints required for public APIs
- Node.js: StandardJS style
- Messages: Follow the [JSON Schema](schemas/message.json) strictly
- Ed25519 signatures: Verify before submitting PRs that change message format

### Pull Request Process

1. Update CHANGELOG.md with your changes
2. Add tests for new features
3. Ensure CI passes (GitHub Actions)
4. Get at least one review from a maintainer

### Protocol Design Principles

- **Keep it simple**: One JSONL file. That's the whole transport.
- **Zero infrastructure first**: File-based IPC before any server-based solution.
- **Cross-language by default**: Every feature must work in Python AND Node.js.
- **Auditability**: Every message is signed and append-only.

---

## 中文 / 贡献指南

### 如何参与

欢迎贡献！Twins Protocol 是一个社区驱动的 AI 协作协议项目。

### 开发环境

```bash
pip install -e .
cd demo/node-side && npm install
pytest tests/
```

### 提交 PR 流程

1. 更新 CHANGELOG.md
2. 为新功能添加测试
3. 确保 CI 通过
4. 获得至少一位维护者审核

### 协议设计原则

- **保持简单**：一个 JSONL 文件就是全部传输层
- **零基础设施优先**：基于文件的 IPC 优先于任何服务器方案
- **默认跨语言**：每个功能必须在 Python 和 Node.js 都可用
- **可审计性**：每条消息签名且只增
