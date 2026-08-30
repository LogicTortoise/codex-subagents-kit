# Decision Matrix

## Layer 1: Do you need more than one agent?

只有当下面至少一项明显成立时，才值得升级：

- `context_protection`
  - 子任务会产生大量主线程不需要记住的噪音
- `parallel_exploration`
  - 多个角度可以正交并行
- `specialization`
  - 工具、权限、领域规则或评估标准明显不同

如果都不明显，选 `single-controller`。

## Layer 2: Ownership shape

| Shape | Best for | Avoid when |
| --- | --- | --- |
| `single-controller` | 单轮、小任务、单文件热点高 | 明显需要并行研究 / 隔离噪音 |
| `manager-with-specialists` | 主控保留最终 synthesis，specialist 只做 bounded sidecar | specialist 需要自己接管用户分支 |
| `handoff-network` | 外部 OpenAI Agents SDK / Responses 方案蓝图 | 当前只是 Codex session 本地执行 |
| `research-shared-findings` | 研究型任务，需要共享发现 | 只是固定顺序流水线 |

## Layer 3: Four Gates

| Gate | Pass when | If not passed |
| --- | --- | --- |
| Product Gate | 所选 subagent runtime CLI 支持当前机制（claude: `--bare` / `--output-format json`；codex: `--output-last-message` / `--json` / `-s` / `-c`） | 不要宣称这是"该 runtime 官方原生路径" |
| Session Gate | 当前 session 确实暴露 native agent 工具证据 | 不要伪装成原生子代理；转 `config-guided` 或 `artifact` |
| Policy Gate | 当前任务、风险、时间、用户要求允许真正 spawn | 退回 controller 或 blueprint |
| Task Gate | 能定义 owner / input / output / acceptance / spawn_reason / stop_condition | 不 spawn |

## Layer 4: Runtime mode (per subagent runtime)

| Runtime | Mode | Use when | Avoid when | Evidence to record |
| --- | --- | --- | --- | --- |
| `claude` | `native-claude-task` | 四层门控都通过，当前 session 有 live native tool evidence | 只有 feature flag 或文档证据，没有 live tools | 版本、feature flag、tool evidence、agent id |
| `claude` | `config-guided-claude-subagents` | 产品层支持，但当前 session 不直接暴露 native tools，或本轮更适合做项目级配置沉淀 | 任务极小、不需要后续复用 | `.claude/agents/`、`CLAUDE.md`、`skills.config` 证据 |
| `codex` | `native-codex-task` | 四层门控都通过 Codex，且有 live Codex tool evidence | 只有 `codex exec --help` 文档证据 | Codex 版本、tool evidence、agent id |
| `codex` | `config-guided-codex-subagents` | `codex exec` 可用，但当前 session 不直接暴露 native tools | 任务极小、不需要后续复用 | `.codex/config.toml`、project rules 证据 |
| both | `artifact-orchestrated-swarm` | 任务值得拆，需稳定降级路径，且 subagent runtime CLI 可用 | 任务太小或没有稳定 I/O | run root、prompt/output/log 结构、降级原因 |

默认 subagent runtime = `claude`。需要在 `init` / `probe` / `task` / `regression` 上加 `--runtime codex` 切换到 mode 2。

## Layer 5: Overlay patterns

- `generator-verifier`
  - 输出质量敏感、rubric 清晰时叠加
- `research-swarm`
  - 多角度资料研究时叠加 shared findings ledger
- `review-separation`
  - 实现者与 reviewer / verifier 分离
- `long-lived-role-ownership`
  - 仅在 runtime 真的支持持久 teammate 时才声称"团队成员持续记忆"

## Spawn Worthiness

一个任务只有同时满足以下条件才值得独立 agent：

1. 单一目标
2. 稳定输入
3. 稳定输出
4. 可写 acceptance
5. 热文件重叠低
6. 可写 stop condition
7. 协调成本 < 收益

## Concurrency Budget

- explorer：2~4
- writer：1~2
- reviewer/verifier：1
- 同热点文件 writer：不并行

## Controller Responsibilities

主控永远保留：

- preflight framing
- mode selection (including runtime choice: claude vs codex)
- registry integrity
- final merge / acceptance
- audit honesty
- scorecard ownership
- stop / fallback ownership
