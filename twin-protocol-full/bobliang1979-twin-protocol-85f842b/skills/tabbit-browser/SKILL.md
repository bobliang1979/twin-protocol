---
name: tabbit-browser
description: "Tabbit AI 原生浏览器的技术与开发技能。Tabbit 是美团光年之外团队推出的 AI-Native 浏览器，内置多 Agent 系统与 Skills 扩展机制。当任务涉及以下场景时使用：(1) 理解 Tabbit 浏览器架构与核心能力 (2) 创建 Tabbit 自定义 Skills（妙招）(3) Tabbit Agent 工作流开发 (4) 内容自动化处理（视频/论文/代码）(5) Tabbit 与第三方工具集成。"
---

# Tabbit Browser 技术技能

## 概述

Tabbit 是美团光年之外（GN06）团队于 2026 年 6 月推出的 AI-Native 浏览器，1.0 正式版实现 Agent 任务完成率从公测 53.1% 提升到 89.7%。
本技能涵盖 Tabbit 的架构原理、Agent 系统、Skills（妙招）开发、工作流编排与集成最佳实践。

## 核心架构

### 分层能力模型

```
Tabbit Browser
├── AI Native 层
│   ├── 多模型网关（GPT-5.5 / Claude 4.7 / Gemini 3.1 Pro / Grok 4.3 / DeepSeek V4 / Kimi K2.6 / Qwen 3.6）
│   ├── 上下文理解引擎（标签页、文件、截图、收藏夹）
│   └── Agent 调度系统
│
├── Agent 系统
│   ├── Research Agent    → 论文/研报深度研读
│   ├── Operator Agent    → 爬虫/表单填写/跨平台数据流转
│   ├── Writer Agent      → 文档/邮件/报告撰写
│   └── Analyst Agent     → 数据处理/情绪分析/趋势发现
│
├── Skills（妙招）引擎
│   ├── 内置 2000+ Skills（覆盖 Top 100 网站日常场景）
│   ├── 自定义 Skills 创建（/ 命令快捷键）
│   └── Skills 市场与共享
│
└── 内容处理管线
    ├── 视频处理（Bilibili HD下载、字幕翻译、弹幕过滤、自动剪辑）
    ├── 论文处理（arXiv/PubMed/PMC/bioRxiv 一键保存、全文查询、表格提取）
    ├── 代码处理（PR Diff解读、测试覆盖检测、Breaking Change 识别）
    ├── 邮件与订阅（去重摘要、付费订阅检测、超时催办排序）
    └── 社交媒体（评论情绪分析、共识/分歧检测）
```

## Agent 系统详解

### 四大 Agent 类型

| Agent | 核心能力 | 典型场景 |
|-------|---------|---------|
| **Research** | 论文研读、文献综述、引用验证 | arXiv 论文全文查询、PubMed 文献聚合、系统性综述追踪 |
| **Operator** | 自动化操作、跨平台流转、表单填写 | 多标签页自动任务、信息提取整合、重复操作自动化 |
| **Writer** | 内容生成、文档撰写、邮件起草 | PR 说明生成、会议纪要、周报自动化 |
| **Analyst** | 数据分析、情绪分析、趋势发现 | 评论区共识挖掘、订阅消费分析、阅读行为画像 |

### Agent 协作模式

Agent 可以协同工作形成自动化流水线：

- Research Agent 收集信息 → Analyst Agent 分析 → Writer Agent 生成报告
- Operator Agent 采集数据 → Analyst Agent 处理 → Writer Agent 输出

## Skills（妙招）开发

### Skills 概念

Tabbit Skills 是用户可自定义的 AI 自动化能力单元，通过 `/` 命令快捷触发。

- **单步 Skill**: 一个 Prompt 模板 + 上下文引用
- **多步工作流**: 多个 Agent 协作的自动化流水线
- **组合 Skill**: 调用外部工具 + AI 处理的混合模式

### Skill 创建模式

#### 1. Prompt 模板型

将重复使用的 Prompt 封装为 Skill，通过 `/skill-name` 快速调用：

```
Skill: /weekly-report
模板: "总结本周 {project} 的进展，重点标注 {key_metrics} 的变化，
      列出阻塞项和下周计划。参考标签页中的 Jira/飞书文档。"
```

#### 2. Agent 工作流型

编排多个 Agent 的执行顺序与数据流转：

```
Skill: /paper-review
步骤:
  1. Research Agent: 从 arXiv/PubMed 获取论文全文
  2. Analyst Agent: 提取方法论、实验数据、关键结论
  3. Writer Agent: 生成结构化综述 + 批判性评注
输出: 完整论文评阅报告
```

#### 3. 内容处理型

利用 Tabbit 内容处理管线能力：

```
Skill: /bilibili-summary
输入: Bilibili 视频链接
处理: HD下载 → 字幕提取 → 内容总结 → 关键片段剪辑
输出: TLDR + 完整文稿 + 精华片段
```

### Skill 开发最佳实践

1. **明确触发条件** — Skill 应有清晰的输入预期和触发场景
2. **分解复杂任务** — 长任务拆分为子 Skill 步骤，提高成功率
3. **引用上下文** — 善用标签页引用、文件引用、截图引用
4. **结果验证** — 关键输出加入验证步骤，确保准确性
5. **迭代优化** — 根据实际执行效果调整 Prompt 模板和工作流

## 典型工作流场景

### 场景 1：每日信息聚合

```
1. Operator Agent 收集 RSS/邮件/订阅 → 去重
2. Analyst Agent 根据阅读历史排序 → 识别关键内容
3. Writer Agent 生成每日摘要卡片
```

### 场景 2：代码评审辅助

```
1. 引用 GitHub PR 页面
2. Research Agent 读取 Diff + 上下文文件
3. Analyst Agent 检测：测试覆盖缺口、Breaking Change、性能风险
4. Writer Agent 生成结构化工审意见
=> 标签页输出结果
```

### 场景 3：学术文献综述

```
1. 提供关键词或论文列表
2. Research Agent: arXiv + PubMed + Semantic Scholar 联合检索
3. Operator Agent: PMC → Unpaywall → preprint 原文获取级联
4. Analyst Agent: 跨论文对比、方法一致性检测、引用验证
5. 输出：结构化综述 + 证据等级标注 + 审计日志
```

### 场景 4：社交媒体分析

```
1. 引用讨论帖/视频评论区
2. Operator Agent 采集全部评论
3. Analyst Agent 分析情绪曲线 → 识别共识/分歧节点
4. 输出：关键分歧摘要 + 情绪可视化 + 有效评论导出
```

## 内容处理管线

### 视频处理

- Bilibili HD 无 watermark 下载（含章节 + 字幕文件）
- 实时字幕翻译（Bilibili → English），无需第三方扩展
- 长视频自动剪辑精华片段（2h → 5min Reel）
- 弹幕智能过滤，按长度/相关性排名

### 论文处理

- arXiv / Nature / PubMed / bioRxiv / medRxiv 一键保存（PDF + 元数据）
- SVM 排名的每日 arXiv 推荐（基于实际阅读行为）
- 跨论文联合查询：表格 TSV 导出、方法论对比
- PMC → Unpaywall → Preprint 原文获取级联（含审计日志）

### 代码/PR 处理

- 大 PR Diff 人类可读解读（Repo-aware）
- Breaking Change 自动检测（rate-limit / cache path 等模式）
- 测试覆盖缺口分析（按 file:line 映射）
- PR 待决事项按超时排序

## Tabbit 与 Codex 的协同

Tabbit Browser 作为 AI-Native 浏览器可以作为 Codex 的外部输入源和操作目标：

```
Codex（当前环境）
  ├── 通过 Chrome 插件控制 Tabbit（Tabbit 基于 Chromium）
  ├── 接收 Tabbit 导出的结构化数据（Markdown / 截图 / 文件）
  └── 反向：Codex 生成的 Skill 配置可导入 Tabbit
```

## 参考资源

### references/
- `skills-development.md` — Tabbit Skills（妙招）开发详细指南
- `agent-workflows.md` — Agent 工作流编排模式参考

### scripts/
- `tabbit-skill-generator.js` — Tabbit Skill 模板生成器

### assets/
- 预留 Tabbit 模板和配置示例文件
