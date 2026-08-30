# Selection Guide

## Step 0: Should this stay single-controller?

默认先问下面 4 个问题：

1. 单控制器 + tools / MCP / scripts 能否完成？
2. 是否真的存在 **context protection** 需求（例如检索噪音、日志、长工具输出）？
3. 是否真的存在 **parallel exploration** 需求（多个角度可正交并行）？
4. 是否真的存在 **specialization** 需求（不同工具/约束/领域规则冲突）？

如果以上信号都不明显，优先保持 `single-controller`。  
多智能体默认是更贵、更复杂、更需要 audit 的路径，不是默认升级。

## Four gates

| Gate | Pass when | If not passed |
| --- | --- | --- |
| Product Gate | 所选 subagent runtime CLI 支持当前机制（claude: `--bare` / `--output-format json` 等；codex: `--output-last-message` / `--json` / `-s` / `-c` 等） | 不要把方案称为"该 runtime 原生已启用" |
| Session Gate | 当前 session 确实暴露 live native child-agent 工具证据 | 不要宣称可直接 native spawn |
| Policy Gate | 当前任务、风险、时间、用户要求允许真正并行/子运行 | 降级到 controller 或 blueprint |
| Task Gate | 能定义 owner / input / output / acceptance / spawn_reason / stop_condition | 不 spawn |

## Ownership-first routing

先决定谁保留最终综合权，再选 subagent runtime：

| Shape | Use when | Avoid when | Notes |
| --- | --- | --- | --- |
| `single-controller` | 任务小、工具足够、并行收益低 | 已存在明显 context pollution / parallel exploration / specialization | 默认首选 |
| `manager-with-specialists` | 主控保留最终 synthesis；specialist 只做 sidecar / verifier / explorer | specialist 需要直接接管分支对话 | 最贴近当前 Codex controller + subagent 路径 |
| `handoff-network` | 你在设计外部 OpenAI Agents SDK / Responses 方案，需要 specialist 接管分支 ownership | 当前任务只是本轮 Codex 本地执行 | 这是架构蓝图术语，不等于当前 session 已具备原生 handoff |
| `research-shared-findings` | 研究型任务中，agent 之间需要复用中途发现 | 工作流主要是固定顺序流水线 | 用共享 findings ledger / registry 近似 shared-state |

## Runtime mode matrix

| Runtime | Mode | Use when | Avoid when | Evidence |
| --- | --- | --- | --- | --- |
| `claude` | `native-claude-task` | 四层门控都通过，且有 live tool evidence | 只有 feature flag / 文档证据 | version + feature + tool evidence |
| `claude` | `config-guided-claude-subagents` | 产品层支持，但当前 session 不适合直接 native spawn；更适合沉淀项目级配置 | 极小任务、不需要复用 | `.claude/agents/`、`skills.config`、`CLAUDE.md` |
| `codex` | `native-codex-task` | 四层门控都通过，且有 live Codex tool evidence | 只有 `codex exec --help` 文档证据 | Codex version + tool evidence |
| `codex` | `config-guided-codex-subagents` | `codex exec` 可用，但当前 session 不适合直接 native spawn；更适合沉淀项目级 Codex 配置 | 极小任务、不需要复用 | `.codex/config.toml`、project rules |
| both | `artifact-orchestrated-swarm` | 任务值得拆，但需要稳定可审计降级路径 | 没有稳定 I/O | `run_root` + prompts/outputs/logs（runtime 记录在 `manifests/run.json`） |
| both | `blueprint-only` | 目标模糊、信息不足、风险高 | 已能直接执行 | 缺失信息与关键假设 |
| both | `single-controller` | 任务小、文件热点高、并行收益低 | 有多份独立输出可并行 | 为什么不值得 spawn |

默认 subagent runtime 是 `claude`。需要在 `init` / `probe` / `task` / `regression` 上加 `--runtime codex` 切换。详见 `references/runtime-modes.md`。

## Pattern overlays

下面这些更像 **overlay**，而不是取代 runtime mode 的第一层分类：

| Overlay | Use when | Key caution |
| --- | --- | --- |
| `generator-verifier` | 输出质量关键，且 rubric 明确可执行 | 没有 rubric 时，verifier 会退化成 rubber stamp |
| `research-swarm` | 需要按角度并行搜索，再合并证据 | explorer 之间必须去重，且要有 no-new-findings stop rule |
| `long-lived-team` | 产品/runtime 明确支持持久 teammate，上下文要跨多任务保留 | 当前 Codex session 默认不要把临时 subagent 误称为长期团队 |

## Spawn worthiness

只有同时满足以下条件才值得独立 agent：

1. 单一目标
2. 稳定输入
3. 稳定输出
4. 可验证 acceptance
5. 热文件重叠低
6. stop condition 可写
7. 协调成本低于收益

额外判断：

- 子任务会不会产生主线程不需要保留的大量噪音？
- 子任务最终能否回传 **短摘要 + 证据指针**？
- explorer 之间能否按角度 / 区域 / 证据类型去重？

## Concurrency budget defaults

- explorer：2~4
- writer：1~2
- reviewer / verifier：1
- 同热点文件 writer：禁止并发

## Default child model policy

- 默认：省略 `model` 与 `reasoning_effort`，让子 agent 继承主会话配置。
- 只有在"成本/时延收益明显大于能力损失"时，才显式下调到 mini 或更低 reasoning。
- 关键路径、方案设计、架构判断、跨证据整合类任务，默认不要降级模型。
- 如果做了模型降级，主控应在 audit / 最终汇报中说明降级原因与影响范围。
- claude runtime 用 `--effort` / `--model`；codex runtime 用 `-c model_reasoning_effort=...` / `-m`。

## Controller ownership

主控永远保留：

- preflight
- mode selection
- registry integrity
- final merge / acceptance
- audit honesty
- scorecard ownership
- stop conditions / fallback ownership
- final decision on what enters `CLAUDE.md` vs tools / MCP / runtime state
