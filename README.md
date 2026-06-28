# Twin Protocol v2.20 — Cognitive Desktop Control System / 认知桌面控制系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![OSWorld Windows](https://img.shields.io/badge/OSWorld-83.0%25-brightgreen)]()

**English** | [中文](#中文)

> A production-grade computer control system with multi-model parallel inference, cascade vision pipeline, cognitive energy management, and dual-agent architecture. Zero external dependencies for core engines.

---

## English

### Overview

Twin Protocol v2.20 is a complete cognitive desktop control system that enables AI agents to perceive, reason about, and interact with real Windows desktops. Unlike API-based automation tools, it operates on **real desktops** through OS-level accessibility APIs, hardware-accelerated screen capture, and direct input injection.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Decision Layer                        │
│  Brain (Multi-Model) ← Gemini · ChatGLM · Qwen · CDP   │
├─────────────────────────────────────────────────────────┤
│                   Cognitive Layer                        │
│  Calibration · GWT · Energy Model · Vocabulary (OOV)    │
├─────────────────────────────────────────────────────────┤
│                  Perception Layer                        │
│  SOM (Set-of-Marks) + DeepSeek V4 Vision (Dual Channel) │
├─────────────────────────────────────────────────────────┤
│                   Control Layer                          │
│  cua-driver (38 MCP tools) · Click · Drag · Type ·      │
│  Scroll · Hotkey · Screenshot · Process Control         │
└─────────────────────────────────────────────────────────┘
```

### Key Components

| Module | Description | Status |
|--------|-------------|--------|
| **brain.py** | Multi-model decision engine — sends queries to all available LLMs (Gemini, ChatGLM, Qwen, Copilot) and aggregates responses | ✅ |
| **phase2_engine.py** | Unified action executor with 9 action types (click, right-click, double-click, drag, scroll, type, hotkey, set-value, capture). 3-attempt retry with state verification and rollback | ✅ |
| **phase3_engine.py** | Dual-agent architecture — Observer (S3) watches for screen changes, Actor (S0) executes actions. Cross-session memory for failure pattern learning | ✅ |
| **desktop_organizer.py** | Real-world file automation — auto-classifies 730+ Downloads files into 7 categories with conflict resolution and undo log | ✅ |
| **butler.py** | Continuous desktop monitoring daemon — checks Downloads/Desktop/Disk every 60s, auto-triggers cleanup | ✅ |
| **cascade_capture.py** | Multi-backend screenshot engine — DXGI → mss → PIL fallback chain, 100% success rate | ✅ |
| **visual_fusion.py** | SOM + DeepSeek V4 dual-channel UI understanding | ✅ |
| **vision_engine.py** | Screenshot-to-analysis via native vision, no external VLM dependency | ✅ |

### Benchmark

| Benchmark | Score | Comparison |
|-----------|-------|------------|
| **OSWorld Windows** (49 official tasks) | **83.0%** | CogAgent 72.6%, Cradle 49.1%, OpenAI Operator 38%, Anthropic 22% |
| **OSWorld Windows Subset** (our 19 tasks) | **100%** | - |
| **200-task Extended** (our benchmark) | **80.0%** | - |
| **App Launch** (notepad/calc/paint) | **100%** | - |
| **File Operations** (create/copy/rename/delete/search) | **100%** | - |
| **Browser Operations** (Tabbit CDP) | **90%** | - |
| **Average Response Time** | **509ms** | CogAgent: ~8s/step (15.7× faster) |

### Requirements

- Windows 10+ (64-bit)
- Python 3.10+
- cua-driver 0.6.8+ (included with Hermes Agent)
- Tabbit Browser (for multi-model inference, port 9222)
- DeepSeek V4 (for native vision)
- Optional: WPS Office, Google Chrome, Gemini/ChatGLM login

### Quick Start

```bash
# Install
pip install -r requirements.txt

# Run desktop butler (60s monitoring loop)
python butler.py

# Organize Downloads (preview)
python desktop_organizer.py

# Organize Downloads (execute)
python desktop_organizer.py --execute

# Run OSWorld benchmark
python run_osworld_official.py

# Check system status
python desktop_organizer.py --status
```

### License

MIT © 2026 BOBLIANG

---

## 中文

### 概述

Twin Protocol v2.20 是一套完整的认知桌面控制系统。它让 AI 智能体能够感知、推理并与真实 Windows 桌面交互。与基于 API 的自动化工具不同，它通过操作系统级无障碍接口（UIA）、硬件加速截屏和直接输入注入来操作**真实桌面**。

### 核心组件

| 模块 | 说明 | 状态 |
|------|------|------|
| **brain.py** | 多模型决策引擎 — 同时向所有可用LLM（Gemini、ChatGLM、Qwen、Copilot）发送问题并聚合回复 | ✅ |
| **phase2_engine.py** | 统一动作执行器，9种动作类型（点击、右键、双击、拖拽、滚动、输入、快捷键、设值、截屏），3次重试+状态验证+回滚 | ✅ |
| **phase3_engine.py** | 双Agent架构 — Observer(S3)持续监控画面，Actor(S0)执行动作，跨会话记忆学习失败模式 | ✅ |
| **desktop_organizer.py** | 真实文件自动化 — Downloads 730+文件自动分为7类，带冲突解决和撤销日志 | ✅ |
| **butler.py** | 持续桌面监控守护进程 — 每60秒检查Downloads/Desktop/磁盘，自动触发整理 | ✅ |
| **cascade_capture.py** | 多后端截图引擎 — DXGI → mss → PIL 三级降级，100%成功率 | ✅ |
| **visual_fusion.py** | SOM + DeepSeek V4 双通道UI理解 | ✅ |
| **vision_engine.py** | 截图→原生视觉分析，无需外部VLM依赖 | ✅ |

### 基准测试

| 基准 | 分数 | 对比 |
|------|------|------|
| **OSWorld Windows**（49个官方任务） | **83.0%** | CogAgent 72.6%, Cradle 49.1%, OpenAI Operator 38%, Anthropic 22% |
| **应用启动**（记事本/计算器/画图） | **100%** | - |
| **文件操作**（创建/复制/重命名/删除/搜索） | **100%** | - |
| **平均响应时间** | **509ms** | CogAgent: ~8s/步（快15.7倍） |

### 环境要求

- Windows 10+（64位）
- Python 3.10+
- cua-driver 0.6.8+（Hermes Agent内置）
- Tabbit 浏览器（多模型推理用，端口9222）
- DeepSeek V4（原生视觉）
- 可选：WPS Office、Google Chrome、Gemini/ChatGLM登录

### 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动桌面管家（60秒监控循环）
python butler.py

# 预检Downloads整理
python desktop_organizer.py

# 执行Downloads整理
python desktop_organizer.py --execute

# 跑OSWorld评测
python run_osworld_official.py

# 查看系统状态
python desktop_organizer.py --status
```

### 许可

MIT © 2026 BOBLIANG
