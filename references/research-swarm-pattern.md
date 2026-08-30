# Research Swarm Pattern

当任务本体是“搜索 / 调研 / 盘点 / 官方资料综述 / 方案对比 / 架构摸底”时读这个文件。

目标不是先讲 skill，而是把任务拆成 **互不重叠、可验证、可合并** 的 research swarm。

## 推荐队形

- controller x1
- explorer x3~4
- synthesizer / verifier x1
- shared findings ledger x1

## 角度切分优先级

优先按下面维度切分，避免多个子 agent 重复搜索同一角度：

1. 主题域：如 security / tools / runtime / evals
2. 证据类型：如官方博客 / 官方 docs / cookbook / API 参考
3. 产品层：如 Anthropic method / OpenAI agents / Codex runtime
4. 时间窗：如最近 6 个月 / 最近 12 个月

优先选择其中一到两种维度形成正交角度，不要四个 explorer 都做“搜多智能体文章”。

## 合同最小格式

每个 spawn-worthy 任务至少写：

- `owner`
- `objective`
- `sources_or_tool_bias`
- `input_path`
- `output_path`
- `acceptance`
- `out_of_scope`
- `stop_condition`

## 控制器保留职责

主控始终保留：

- provisional preflight
- four-gate judgment
- angle map
- dedupe / merge
- conflict resolution
- final audit / scorecard

## Shared findings ledger

研究型 swarm 默认维护一个共享 findings 文档，至少包含：

- `claim`
- `source`
- `why_it_matters`
- `confidence`
- `duplicate_of`

explorer 写入前先查重；如果主要目标变成“共享情报”，不要把它误写成 message bus。

## 停止条件

研究型 swarm 至少配置其中 2 项：

1. 最大轮数
2. 时间预算
3. 连续 N 轮无新发现
4. verifier 认为已足够回答问题
5. 主控选择 best-effort merge 并显式记录剩余空白

## 官方资料类任务的最小蓝图

- `controller`
  - objective: 定义问题边界、角度地图、输出 schema、合并标准
- `explorer-anthropic`
  - objective: 只收集 Anthropic 官方博客 / docs 的相关材料
- `explorer-openai`
  - objective: 只收集 OpenAI / Codex 官方博客 / docs / cookbook 的相关材料
- `explorer-gap-review`
  - objective: 只审查本地 skill 与当前方法论 / runtime 的差距
- `verifier-synthesizer`
  - objective: 去重、标日期、标冲突、补不确定性说明、产出综合蓝图

## 合并与核验

最终汇总前至少检查：

1. 是否重复记录了同一篇资料
2. 是否标出来源链接
3. 是否区分“官方明确写了什么”和“主控的工程推断”
4. 是否写清推荐模式 / overlay / runtime path
5. 是否保留剩余空白与后续验证项
