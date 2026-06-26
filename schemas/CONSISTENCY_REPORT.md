# Spec-Consistency Report: TWINS_PROTOCOL.md vs JSON Schemas

## Summary: 6 discrepancies found (3 schema-extra, 3 spec-only)

## A) In schemas but missing from spec (add to spec v0.2)

| Field | Schema | Why |
|-------|--------|-----|
| tool_result.execution_ms | tool_result.json | 工具执行耗时，性能监控必需 |
| tool_result._ts | tool_result.json | 结果生成时间戳 |
| state_update.state.last_seen_ts | state_update.json | 防重放：接收方记录最后处理时间 |
| shared_cognition._ts | shared_cognition.json | 认知层更新时间戳 |
| shared_cognition.agent_a.last_reply_ts | shared_cognition.json | 对称时间追踪 |

## B) In spec but not covered by schemas

| Feature | Location in Spec | Action |
|---------|-----------------|--------|
| 多行 JSON 支持 | "支持多行 JSON（brace matching）" | v0.1 先声明"未来支持"，当前强制单行 |
| 安全认证 | 安全章节 | v0.2 再添加 auth schema |
| 超时机制 | "60s 无 response 视为失败" | tool_request schema 加 timeout 字段 |
| 幂等存储 | ".processed_ids.txt" | 实现细节，非 schema 层 |

## C) Naming

Two schema files exist:
- twin-protocol/schemas/*.json (per-type, Codex++)
- Hermes's twins_schema.json (all-in-one)

→ 不冲突，各有用途。建议 twins_schema.json 放根目录供 CLI 用，schemas/ 放子目录供引用。
