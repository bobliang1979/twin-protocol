# Phase 3 审计：v4.0 Absolute ↔ v5.3 L5 Hardened 持久化层对比

**审计时间：** 2026-06-26
**基线：** `astraea_v4_0_absolute.py` (321 行) — 生产 MCTS 推理引擎
**目标：** `astraea_v5_3_hardened.py` (647 行) — 自进化运行时的持久化/AST/热交换层
**验证状态：** Phase 2 (18/18) + Pipeline (5/5) = **23/23 全 PASS**

---

## 1. 架构对比矩阵

| 维度 | v4.0 Absolute | v5.3 L5 Hardened | 交集 / 差异 |
|---|---|---|---|
| **核心目标** | MCTS 推理管道 | 自进化代码运行时 | 不同范式：推理 vs 进化 |
| **数据结构** | `StructuredReasoningNode` (树) | `AsyncPersistentSelf` (SQLite 表) | 无重叠——v4.0 无持久化 |
| **安全** | 无 AST 守卫 | `ast_guard_sandbox()` + 列白名单 | v4.0 缺乏注入防御 |
| **持久化** | 无（纯内存） | aiosqlite + asyncio.Lock + 4 表 | **v4.0 主要缺口** |
| **Token 不变性** | sha256 不可变 kv_cache_token | 无等价物 | v5.3 无链式 provenance |
| **断路器** | `_verify_chain_liveness()` | 无 | v5.3 无突变链保护 |
| **重试/回滚** | 隐式（penalty backprop） | 显式 `record_rollback()` | 互补 |

---

## 2. 关键发现：6 个具体缺口

### 2.1 持久化不兼容 [严重]
v4.0 的 `StructuredReasoningNode` 树**完全没有持久化能力**。v5.3 的 `AsyncPersistentSelf` 可以存 self-model、mutation_history、telemetry、learned patterns——但**没有一个表支持树状推理结构**。

**差距：** 需要一个 `reasoning_tree` 表来持久化 MCTS 树，包含：
- node_id (UUID), parent_id (FK→self), kv_cache_token, state_json, visits, total_value, depth
- 与 v4.0 的 genesis liveness 语义兼容（weakref 不可序列化，需转为外键引用）

### 2.2 Token 链 vs Payload Hash [中]
- v4.0: `kv_cache_token = sha256(parent_token + state)` — 链式不可变，完整 provenance
- v5.3: `payload_hash = sha256(code)[:16]` — 只对代码本身哈希，不追踪来源
- **风险：** v5.3 的 mutation_history 无法验证突变序列的因果完整性

### 2.3 AST Guard 可注入 v4.0 管道 [低]
v5.3 的 `ast_guard_sandbox()` 能在生成后、节点创建前作为预提交钩子注入 v4.0 的 `batch_expand_and_evaluate()`。v4.0 当前接受任何 `json.loads(raw)`——若 generator 被注入危险代码，无防御。

**建议：** 在 v4.0 line 231（`child = StructuredReasoningNode(...)` 之前）插入 AST 校验。

### 2.4 断路器缺口 [中]
v4.0 有 `_verify_chain_liveness()` 检测 I/O 挂起期间的 lineage 失效。v5.3 的 `ModuleHotSwapper.apply_mutation()` 在热交换后无等价检查——若 importlib 加载损坏模块，状态被静默破坏。

**建议：** v5.3 在 `exec_module()` 后增加 `import_error_circuit_breaker` 监控。

### 2.5 列白名单 vs 字段完整性 [低]
v5.3 的 `validate_column()` / `validate_columns()` 是 SQL 注入防御，但**不验证值类型**。v4.0 的 `total_value` 是 float，若通过 v5.3 的 save() 传入字符串，会在下一次 `avg_value` 计算时静默 NaN。

### 2.6 v5.3 缺少 Wilson Score [中]
v5.3 用硬编码置信度更新（`+0.05` / `-0.02`）驱动进化，无统计收敛度量。v4.0 的 Wilson Score 可作为 v5.3 的置信度更新策略——替代线性步长。

---

## 3. 合并路线图（建议优先级）

```
Phase 3a [P0]: 将 AsyncPersistentSelf 适配为 v4.0 持久化后端
  ├─ reasoning_tree 表 DDL
  ├─ serialize_node / load_tree 递归
  └─ weakref→UUID 外键转换

Phase 3b [P1]: AST Guard 注入 v4.0 管道
  └─ batch_expand_and_evaluate line 231: ast_guard(json_schema) pre-commit

Phase 3c [P2]: v5.3 增加 Wilson Score 置信度策略
  └─ 替代硬编码 +0.05 / -0.02 步长

Phase 3d [P2]: v5.3 增加突变链断路器
  └─ ModuleHotSwapper 增加 lineage hash 链 + 验证
```

---

## 4. v4.0 Absolute 封版验证总结

| 维度 | 状态 | 证据 |
|---|---|---|
| 数学连续性 (log(v+1)) | ✅ Phase 2 | UCT Continuity (4/4) |
| Wilson 域双钳制 | ✅ Phase 2 | Wilson Domain (5/5) |
| 创世活性 (weakref) | ✅ Phase 2 | Genesis Liveness (5/5) |
| Token 不变性 (sha256) | ✅ Phase 2 | Token Invariance (4/4) |
| 管道收敛 3 轮 | ✅ Pipeline | test 1 |
| 管道收敛 8 轮 | ✅ Pipeline | test 2, visits≥3 avg≤1 |
| 断路器（深度限制） | ✅ Pipeline | test 3, max_depth≤2 |
| 死路惩罚 | ✅ Pipeline | test 4, 无异常 |
| 语义去重 | ✅ Pipeline | test 5, 去重正确 |
| 总计 | **23/23 PASS** | — |

v4.0 Absolute 可以**正式封版**。后续 Phase 3 工作在此之上附加持久化层，不修改核心数学语义。
