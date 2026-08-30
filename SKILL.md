---
name: codex-subagents-kit
description: Codex 专用多智能体 / 子智能体编排工作台，**双 subagent runtime** 可切换。默认 mode 1 = Claude Code CLI (`claude -p --bare --output-format json`)；mode 2 = Codex CLI (`codex exec -c model_reasoning_effort=xhigh -s workspace-write -C WS --output-last-message OUT --json`)。自带可执行 CLI `codex-subagent` (子命令 `init` / `probe` / `check` / `task` / `regression`)；`task` 直接 spawn 对应 runtime 子进程作为 subagent，artifact-orchestrated 模式。用于判断任务应保持单控制器，还是升级为 manager-with-specialists、generator-verifier、research-swarm、`.claude/agents/`、`CLAUDE.md`、`settings.json`、`.codex/config.toml` 等 artifact-backed execution path。适用于需要控制上下文污染、选择协作拓扑、并用 runtime probe / audit / scorecard 验证方案的场景。
---

# Codex Subagents Kit

把这个 skill 当成 **Codex → subagent 编排桥**：

- 默认 subagent runtime = **Claude Code CLI** (`claude -p --bare --output-format json`)
- 备选 subagent runtime = **Codex CLI** (`codex exec ... --output-last-message ... --json`)
- Codex 自己仍然是 **controller / orchestrator**，不直接执行子任务
- 子任务全部 artifact-orchestrated：每个 child = 一个 prompt 文件 + 一个 output 文件 + 一个 log
- 吸收 Anthropic / OpenAI / Codex 官方方法论：**single-controller first、context-centric decomposition、ownership-first routing、summary-only returns**
- 控制上下文体积，避免把长说明塞进主对话
- 用可验证 artifacts、脚本和 scorecard 构成闭环
- 对 native child-agent 能力保持诚实；证据不足时改走 artifact 路径

## Two Runtimes (Mode 1 / Mode 2)

通过 `--runtime claude` 或 `--runtime codex` 切换 subagent runtime。两种 runtime 共用同一份 artifact 合同、registry、scorecard、audit、四层门控。

| Mode | Runtime | CLI | 配置 / 凭据 | 输出 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 (default) | `claude` | `claude -p --bare --output-format json` | `ANTHROPIC_API_KEY` 或 `apiKeyHelper` in `~/.claude/settings.json` | JSON envelope → 解析 `result` 字段 | `--bare` 模式跳过 hooks / LSP / plugin / CLAUDE.md auto-discovery；OAuth-only 时回退 `--no-bare` |
| 2 | `codex` | `codex exec -c model_reasoning_effort=xhigh -s workspace-write -C WS --output-last-message OUT --json` | Codex CLI 的 provider auth | stdout JSONL events + `--output-last-message` 写入最终 assistant 文本 | 用同一份 prompt / output / log 路径；JSONL 落 `logs/*.json`，last message 落 `outputs/*.md` |

切换例子：

```bash
# 默认 (mode 1)
codex-subagent init    --workspace-root . --case my-task
codex-subagent probe   --run-root .workspace/codex-subagents-kit/runs/<run_id> --workspace-root .
codex-subagent task    --run-root .workspace/codex-subagents-kit/runs/<run_id> \
                       --prompt-file  .workspace/.../prompts/task-a.md \
                       --output-file  .workspace/.../outputs/task-a.md

# 切到 mode 2：在 init / probe / task / regression 上加 --runtime codex
codex-subagent init    --runtime codex --workspace-root . --case my-task --runtime codex
codex-subagent probe   --runtime codex --run-root ... --workspace-root ...
codex-subagent task    --runtime codex --run-root ... --prompt-file ... --output-file ...
```

`check` 是 runtime-agnostic：它从 `manifests/run.json` 读 `runtime` 字段决定 native-mode 的 claim 名 (`native-claude-task` vs `native-codex-task`)。

详细对比：见 `references/runtime-modes.md`。
本机事实：见 `references/claude-runtime-notes.md` 和 `references/codex-runtime-notes.md`。

## Why these two runtimes

**Claude Code CLI 作为默认**：

- Anthropic Claude Code 的 `-p --bare` 模式专门为 scripted / SDK 调用设计
- `--bare` 跳过 hooks / LSP / plugin sync / attribution / auto-memory / CLAUDE.md auto-discovery / keychain
- 显式 context 必须通过 `--system-prompt[-file]`、`--append-system-prompt[-file]`、`--add-dir`、`--mcp-config`、`--settings`、`--agents`、`--plugin-dir` 提供
- `--output-format json` 输出结构化结果 (`stream-json` 支持实时流式)
- `--max-budget-usd` 给硬性 stop condition
- `--allowedTools` / `--disallowedTools` 收紧子 agent 工具面
- `--session-id` 可追踪每个 child run
- `--no-session-persistence` 让子任务不污染全局 session 历史

**Codex CLI 作为备选 (mode 2)**：

- Codex `codex exec` 本身就是非交互入口，适合 orchestrated spawn
- `--output-last-message <file>` 直接落最终 assistant 文本到文件
- `--json` 把 streaming events 写成 JSONL 到 stdout
- `-c model_reasoning_effort=xhigh` 显式控制 reasoning 档位
- `-s workspace-write` 默认 sandbox；需要更宽权限时再升级
- `--skip-git-repo-check` 让 Codex 在非 git 仓库也能跑
- `--ephemeral` 完全不持久化 session
- `--add-dir` 控制额外可访问目录
- provider auth 走 Codex CLI 自己的 config，不需要单独配 ANTHROPIC_API_KEY

来源：本机 `claude --version` → `2.1.251 (Claude Code)`；`codex --version` → `codex-cli 0.144.1`。CLI 表面已用 `claude --help` / `claude -p --help` / `codex exec --help` 核对。

## Core rules

1. 先做 preflight，再决定是否并行。
2. 默认先尝试 **single-controller / one-agent-with-tools**；只有在 **context protection、parallel exploration、specialization** 其中至少一项明显成立时才升级。
3. 先决定 **ownership**，再决定 topology：谁保留最终综合权，谁只做 sidecar，谁只做 verifier。
4. 区分 **产品支持**、**会话证据**、**策略许可**、**任务适配** 四层事实。
5. 只把独立、边界清晰、验收明确、返回可摘要的任务交给子 agent。
6. 分工优先按 **上下文边界** 拆，不按岗位头衔机械拆。
7. 所有循环都必须有 **stop condition / time budget / fallback**。
8. 长计划、长结果、对比表优先落盘，不优先塞进聊天上下文；子 agent 默认只回传 **evidence-dense summary**。
9. 规则性动作优先脚本/CLI，不要把一切都做成 agent；工具、MCP、`CLAUDE.md`、state 归属要写清。
10. **默认不要下调子 agent 模型档位**：除非用户明确要求省钱/提速，或任务是低风险、低复杂度 sidecar，否则不要显式把子 agent 改成更小模型。
11. **默认继承主控模型与 thinking effort**：调用 `claude -p` 或 `codex exec` 时优先省略 `--model` / `--effort` / `-m`，让 child 沿用 environment 默认；只有在你能说明收益和风险时才覆盖。

## Default subagent model policy

- **默认策略**：子 agent 不传 `--model`、不传 `--effort`、不传 `-m`，继承 environment 默认。
- **允许降级的场景**：
  1. 用户明确要求更便宜 / 更快
  2. 大规模并行探索，且每个子任务都很轻、验收清晰
  3. 低风险信息收集 sidecar，不阻塞关键路径
- **降级后的义务**：如果显式改用 `--model sonnet` 或 `--effort low`，必须在最终说明里写清楚"为什么降级、收益是什么、潜在损失是什么"。

## Minimal workflow

### 1) Preflight

先写清一版 **provisional preflight**：

- `final_goal`
- `deliverables`
- `constraints`
- `success_criteria`
- `spawn_candidates`
- `tasks_not_worth_spawning`

如果用户 prompt 已经隐含了这些信息，就直接提炼一版简洁 preflight，不要机械地回问字段名。  
只有当缺失信息会改变 **mode selection / acceptance / audit 结论** 时，才向用户追问。

复杂任务先初始化 run：

```bash
# 默认 claude 模式
codex-subagent init \
  --workspace-root . --case my-task

# 显式切到 codex 模式 (mode 2)
codex-subagent init \
  --workspace-root . --case my-task --runtime codex
```

最小 artifacts：

- `preflight.md`
- `agent-blueprints.md`
- `execution-plan.md`
- `task-registry.md`
- `protocol-audit.md`
- `team-report.md`
- `scorecard.md`

当 run 使用 `v2` 合同时，`task-registry.md` 还应补齐：

- `Stop Condition`
- `Escalation / Fallback`
- `Evidence Path`

### 2) Four gates

先判断四层门控：

1. **Product Gate**：所选 runtime CLI 是否支持当前机制 (claude 检查 `--bare` / `--output-format json` 等；codex 检查 `codex exec --help` 是否支持 `--output-last-message` / `--json` / `-s` / `-c`)
2. **Session Gate**：当前 session 是否有 live native agent 工具证据 (Claude Code 的 `Task` 工具，或 Codex 的 `spawn_agent` 等)
3. **Policy Gate**：当前任务/风险/用户要求是否允许真正 spawn
4. **Task Gate**：能否写出 owner / input / output / acceptance

`probe` 子命令会把所有 4 层门控写到 `manifests/runtime-probe.json`，并给出 `assessment.recommended_mode`。

如果需要完整判断规则，读：

- `references/selection-guide.md`
- `references/claude-runtime-notes.md`
- `references/codex-runtime-notes.md`

### 3) Decide whether multi-agent is warranted

先问：

- 单控制器 + tools 能否完成？
- 是否真的存在 `context protection / parallel exploration / specialization`？
- 子任务是否能只回传高信号摘要，而不是把原始噪音倒回主线程？

如果答案偏否，优先保持 `single-controller`。

### 4) Choose ownership and overlays

先决定谁保留最终综合权：

- `manager-with-specialists`
  - 主控保留最终 synthesis；specialist 只负责 sidecar / tool-like 工作
- `handoff-network`
  - 更适合外部 Anthropic Agent SDK / OpenAI Agents SDK 方案蓝图；不要把它误称为当前 Codex session 的原生 handoff
- `generator-verifier`
  - 作为验证覆盖层附着在其他模式之上；只有 rubric 明确时才值得加
- `research-swarm / shared-findings`
  - 研究型任务专用；用共享 findings ledger + 角度去重 + 停止条件，而不是让所有 explorer 搜同一件事

### 5) Choose a runtime mode

默认只在四层门控都通过时选 `native-claude-task` 或 `native-codex-task`。  
否则按任务目标选择：

- `single-controller`
- `config-guided-claude-subagents` / `config-guided-codex-subagents`
- `artifact-orchestrated-swarm` ← **默认 fallback**

工程快速路由提示 (这是**基于官方原则落地到本 skill 的工程推断**，不是产品层硬保证)：

- 当 prompt 明确要求 `angle-map / shared-findings / dedupe / official-vs-inference / gap review` 这类研究交付物时，优先评估 `research-swarm`
- 当 prompt 明确要求 `.claude/agents / settings.json / team templates`，且 session 级 native 证据不确定时，优先评估 `manager-with-specialists + config-guided-claude-subagents`
- 当 prompt 明确要求 `run_root / per-task prompt-output / registry / protocol-audit / scorecard / replayable artifacts` 时，优先评估 `manager-with-specialists + artifact-orchestrated-swarm` (默认 claude runtime)
- 当任务只是**给出 routing / topology / mode 决策**，而不是要求你立刻实际启动 child agents 时，`manager-with-specialists` 默认优先落到 `config-guided-claude-subagents`；只有在 prompt 明确要求实际 live native delegation，或当前执行确实要马上使用子 agent 时，才优先写成 `native-claude-task` 或 `native-codex-task`
- 当 prompt 明确要求 "用 Codex 跑子任务 / spawn Codex / `codex exec`"，或者当前主控 session 不是 Claude Code / Codex CLI 但需要保留 Codex CLI 体系时，优先选 `native-codex-task` (mode 2)

如果这些 lexical cues 与四层门控冲突，以门控诚实性优先；不要为了命中模式名而伪造 native 证据。

如果需要完整模式矩阵，读：

- `references/selection-guide.md`
- `references/runtime-modes.md`

### 6) Keep context small

默认只读：

- 当前 `SKILL.md`
- 与当前决策直接相关的少量 reference
- 必要入口文件

不要默认读完所有 references、logs、历史会话。

如果需要更细的 token 控制规则，读：

- `references/context-efficiency.md`

### 7) Use project agents when config-guided mode wins

当产品层支持，但当前 session 不适合直接 native spawn 时：

**claude runtime**：

1. 优先在项目里维护 `.claude/agents/`
2. 保持 `CLAUDE.md` 简短，只放高复用协作规则
3. 用 `settings.json` 精确配置 permissions / hooks / mcp
4. 用固定模板定义 explorer / worker / reviewer / verifier
5. 明确哪些规则应该进 `CLAUDE.md`，哪些应该留在 task-specific prompt / MCP / runtime state 中

**codex runtime**：

1. 优先在 `~/.codex/config.toml` + `.codex/config.toml` 里维护 provider / sandbox / approval 策略
2. `codex-subagent regression --runtime codex` 不写 `.claude/agents/` (Codex 没有等价配置目录)

如果需要模板与复制规则，读：

- `references/project-agents.md`
- `assets/project-agents/*.toml` (claude runtime only)

### 8) Use artifact swarm when a stable artifact path is needed

当需要稳定降级路径时：

1. 每个子任务写独立 prompt
2. 每个子任务写独立 output file
3. 通过 `codex-subagent task` 执行 (内部按 `--runtime` 走 claude-p-bare 或 codex exec)
4. 持续维护 registry / audit / scorecard
5. 对 research / review 类任务，优先让 child 输出结构化 findings，而不是长篇过程日志

执行子任务优先用：

```bash
# claude runtime (default)
codex-subagent task \
  --run-root .workspace/codex-subagents-kit/runs/<run_id> \
  --prompt-file .workspace/.../prompts/task-a.md \
  --output-file .workspace/.../outputs/task-a.md

# codex runtime (mode 2)
codex-subagent task --runtime codex \
  --run-root .workspace/codex-subagents-kit/runs/<run_id> \
  --prompt-file .workspace/.../prompts/task-a.md \
  --output-file .workspace/.../outputs/task-a.md
```

默认 child invocation：

```bash
# mode 1 (claude)
claude -p --bare \
  --output-format json \
  --no-session-persistence \
  --max-budget-usd N \
  --allowedTools "Read,Grep,Glob,Bash(limited)" \
  --add-dir <workspace> \
  --session-id <uuid> \
  --append-system-prompt-file <file> \
  -

# mode 2 (codex)
codex exec \
  -c model_reasoning_effort=xhigh \
  -c tool_output_token_limit=500000 \
  -s workspace-write \
  -C <workspace> \
  --add-dir <extra> \
  --skip-git-repo-check \
  -o <output_file> \
  --json \
  -
```

如果需要 child prompt 合同、热文件规则、reviewer 分离规则，读：

- `references/multi-agent-hardening.md`
- `references/topology-catalog.md`
- `references/artifact-contract.md`

### 9) Probe and validate

需要 runtime 证据时执行：

```bash
codex-subagent probe --runtime claude \
  --run-root .workspace/codex-subagents-kit/runs/<run_id> --workspace-root .

# 或 codex runtime
codex-subagent probe --runtime codex \
  --run-root .workspace/codex-subagents-kit/runs/<run_id> --workspace-root .
```

完成后先校验：

```bash
codex-subagent check \
  --run-root .workspace/codex-subagents-kit/runs/<run_id>
```

如果需要做真实 prompt 的 forward-test / regression，优先复用同一 `run_root`：

```bash
# claude
codex-subagent regression --runtime claude --testbed-root <tmp>

# codex
codex-subagent regression --runtime codex --testbed-root <tmp>
```

加 `--execute` 才会真正 spawn children；默认 dry-run 只构造命令。

1. 保留 `runtime-probe.json`
2. 把 prompt、output、log 落到 run artifacts
3. 用 scorecard 区分 **官方方法论映射** 与 **工程闭环**
4. 只有在得分提高且无关键维度退化时，才把改动回写到 skill 本体

## Output contract

最终回答至少说明：

1. 是否真的值得多智能体；如果不值得，为什么保持单控制器
2. 选了哪个 subagent runtime (claude 还是 codex) 以及为什么
3. ownership shape / overlay 选择了什么
4. 四层门控的判断结果
5. 是否真的用了对应 runtime 物理 spawn，还是 config-guided / single-controller
6. `run_root` 和主要 artifacts
7. 哪些任务值得 spawn，哪些不值得
8. 哪些上下文被刻意不加载，以节省 token
9. `CLAUDE.md` / tools / MCP / state / approvals / Codex sandbox 的边界决策
10. 停止条件、fallback、评估或 verifier 计划
11. 如果覆盖了 `--model` / `--effort` / `-m` / reasoning_effort，覆盖原因是什么

## Read-on-demand map

- `references/official-patterns-2026.md`
  - 需要对齐 Anthropic 五模式、OpenAI ownership/handoff、Codex subagents 最新官方方法论时读
- `references/selection-guide.md`
  - 需要判断"是否值得多智能体"、ownership shape、runtime 模式矩阵、并发预算时读
- `references/runtime-modes.md`
  - 需要看清 claude vs codex 两种 runtime 的细节对比 (flags、output、config、auth、回归表现) 时读
- `references/context-efficiency.md`
  - 需要控制 token / prompt 体积时读
- `references/project-agents.md`
  - 需要落地 `.claude/agents/` 模板时读
- `references/topology-catalog.md`
  - 需要选择研究/修复/审查队形时读
- `references/research-swarm-pattern.md`
  - 需要把资料研究任务拆成去重的 explorer 角度、共享 findings、收敛/停止条件时读
- `references/multi-agent-hardening.md`
  - 需要 prompt 合同、热文件规则、review 分离、summary-only return、stop condition 时读
- `references/artifact-contract.md`
  - 需要 artifacts / audit / scorecard 规范时读
- `references/scoring-rubric.md`
  - 需要把 OpenAI / Anthropic / Codex 方法论映射成 forward-test / regression 评分维度时读
- `references/claude-runtime-notes.md`
  - 需要本机 Claude Code CLI 已知事实时读
- `references/codex-runtime-notes.md`
  - 需要本机 Codex CLI 已知事实时读
- `references/decision-matrix.md`
  - 需要快速回看"是否多 agent / ownership / 四门控 / runtime mode / overlay" 五层决策表时读
