# Official Patterns 2026

把这个文件当成 **外部官方方法论桥接层**：它不定义当前 session 是否真的支持某能力，而是帮助你把 Anthropic 与 OpenAI / Codex 官方材料转成 Codex skill 规则。

## Source map

### Anthropic

- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents?cam=claude)
  - 先从简单可行方案开始，不迷信复杂框架
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
  - 研究型多 agent 的广搜、分工、评估与可观测性
- [Building agents with Skills: Equipping agents for specialized work](https://claude.com/blog/building-agents-with-skills-equipping-agents-for-specialized-work)
  - Skills 作为能力封装层，强调 progressive disclosure
- [Building multi-agent systems: When and how to use them](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)
  - `context-centric decomposition`
- [Multi-agent coordination patterns: Five approaches and when to use them](https://claude.com/blog/multi-agent-coordination-patterns)
  - generator-verifier / orchestrator-subagent / agent teams / message bus / shared state

### OpenAI / Codex

- [A practical guide to building AI agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
  - single-agent-first，必要时再加 specialist
- [Agents SDK](https://developers.openai.com/api/docs/guides/agents)
  - state、orchestration、approvals、observability
- [Orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration)
  - ownership-first：handoff vs manager-with-specialists
- [Using tools](https://developers.openai.com/api/docs/guides/tools)
  - tools / MCP / built-ins 是主路径，不只是附属功能
- [Custom instructions with CLAUDE.md](https://developers.openai.com/claude/guides/agents-md)
  - `CLAUDE.md` 的加载层级和职责边界
- [Subagents](https://developers.openai.com/claude/concepts/subagents)
  - 用子 agent 处理噪音、并行和隔离，且需要显式触发
- [Best practices](https://developers.openai.com/claude/learn/best-practices)
  - task-per-thread、tests / review / evidence loop

## Cross-source synthesis

### 1) Single-controller first

Anthropic 和 OpenAI 都强调：  
先从最简单可行形态开始。对于这个 skill，默认路由应该是：

1. `single-controller`
2. `manager-with-specialists`
3. `native-claude-task` / `config-guided-claude-subagents` / `artifact-orchestrated-swarm`

不要默认从“我们要不要组一个团队”开始。

### 2) Context-centric decomposition beats title-centric decomposition

Anthropic 明确强调按上下文边界拆，而不是按岗位头衔拆。  
OpenAI / Codex 则从另一个角度支持这条：子 agent 的价值之一是隔离 exploration noise、保住主线程上下文。

因此：

- 优先拆独立角度、独立文件边界、独立证据域
- 不要默认 planner / implementer / tester / reviewer 各来一个

### 3) Ownership first, topology second, runtime third

综合后可落成三层决策：

1. `Do we need more than one agent?`
2. `Who owns final synthesis?`
3. `Which Codex runtime path is honest here?`

这比直接上“五选一模式菜单”更适合当前 Codex skill。

### 4) Treat generator-verifier as an overlay

Anthropic 的 generator-verifier 很强，但前提是 rubric 明确。  
在这个 skill 里，更稳妥的实现通常是：

- `research-swarm + verifier`
- `delivery-swarm + verifier`
- `single-controller + verifier`

而不是把 verifier 当成总架构本体。

### 5) Shared-state ideas can be approximated with files

OpenAI / Codex 当前更强调 state、tools、MCP、CLAUDE.md，而不是把 `shared state` 当成首页拓扑。  
在 Codex skill 中，可用下面方式近似 shared-state：

- shared findings ledger
- task registry
- evidence log
- structured notes

### 6) Tools, MCP, CLAUDE.md, and runtime state are different layers

默认边界：

- `CLAUDE.md`
  - repo norms、build/test/lint、工程约束、done 定义
- tools / MCP
  - 外部活数据、系统接口、工具能力
- runtime state
  - 本轮会话进度、findings、temporary decisions

不要把这三类信息混成一个超长 prompt。

### 7) Stop conditions and evals are first-class

Anthropic 强调 reactive loop / endless review loop 风险。  
OpenAI 强调 trace grading、agent evals、approvals。

因此每个 swarm 方案至少要定义：

- max rounds / time budget / no-new-findings threshold
- fallback
- verifier / grader
- evidence to inspect

## Translation to this skill

当你更新本 skill 时，优先检查：

1. 是否默认保留 `single-controller first`
2. 是否先做 ownership 判断
3. 是否把 `generator-verifier` 视为 overlay
4. 是否给 research 任务单独的 shared findings 方案
5. 是否区分 `CLAUDE.md` / tools / MCP / runtime state
6. 是否要求 summary-only return
7. 是否把 stop conditions / evals / audit 写成默认输出
