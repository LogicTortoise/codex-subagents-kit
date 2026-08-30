# Topology Catalog

## manager-with-specialists

- controller x1
- specialist x1~3
- verifier x0~1
- 适合：主控保留最终综合权，specialist 只做 bounded explorer / reviewer / verifier / tool-like work
- 备注：这是当前 Codex session 最常见的默认形态

## research-swarm

- controller x1
- explorer x2~3
- synthesizer/reviewer x1
- shared findings ledger x1
- 适合：资料调研、架构摸底、最佳实践对比
- 关键规则：按角度去重；默认只回传高信号摘要；必须有 no-new-findings / time-budget stop condition

## delivery-swarm

- controller x1
- explorer x1
- worker x1~2
- verifier x1
- 适合：中等规模实现 + 回归

## bugfix-swarm

- reproducer x1
- root-cause explorer x1
- patch worker x1
- regression verifier x1
- 适合：Bug 复现、根因分析、修复、回归闭环

## review-swarm

- controller x1
- code reviewer x1
- security reviewer x1
- docs reviewer x1
- 适合：PR 审查、变更风险评估、交付前检查

## generator-verifier overlay

- generator x1
- verifier x1
- 适合：输出质量关键，且 rubric / pass-fail 标准明确
- 关键规则：没有 rubric 时不要机械叠加 verifier

## long-lived-team note

- 只有在产品/runtime 明确支持持久 teammate 和记忆保留时，才称其为 `agent team`
- 当前 Codex session 默认更适合声称为 `manager-with-specialists` 或 `research-swarm`

## Concurrency Budget Defaults

- explorer: 2~4
- writer: 1~2
- reviewer/verifier: 1
- same hot file writers: 0 concurrent

若没有 worktree / branch / file partition 证据，不要提升 writer 并发。
