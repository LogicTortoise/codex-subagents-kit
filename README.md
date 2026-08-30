# codex-subagents-kit

> A Codex-side controller that orchestrates subagent runs through **two interchangeable runtimes**: Claude Code CLI (default) or Codex CLI itself.

Codex is the controller. Subagent work runs in artifact-orchestrated child processes whose prompts and outputs are written to disk, scored against an audit contract, and kept auditable end-to-end. Both runtimes share the same artifact format, registry, scorecard, and four-gate model — only the child command shape and the runtime-specific config change.

## Why this exists

Multi-agent work has three failure modes this kit is built to avoid:

1. **Context pollution.** Long logs and tool outputs dump back into the main thread.
2. **Native-tool fake claims.** Code claims a subagent path that the runtime does not actually support.
3. **Non-replayable runs.** Spawn results cannot be re-run, audited, or rolled back.

`codex-subagents-kit` makes every child run:

- **Artifact-backed**: each task has a prompt file, an output file, and a raw log.
- **Runtime-honest**: a four-gate probe (`product / session / policy / task`) decides whether native spawn is allowed; otherwise it falls back to config-guided or single-controller mode.
- **Replayable**: every run lives under `.workspace/codex-subagents-kit/runs/<run_id>/` and can be re-checked with `codex-subagent check`.

## Two runtimes (mode 1 / mode 2)

| Mode | Runtime | Default child command | Auth | Config artifact |
| --- | --- | --- | --- | --- |
| **1 (default)** | `claude` | `claude -p --bare --output-format json --no-session-persistence --max-budget-usd 5 --allowedTools "Read,Grep,Glob" --disallowedTools "WebFetch,WebSearch" --permission-mode bypassPermissions --add-dir WS --session-id UUID` | `ANTHROPIC_API_KEY` or `apiKeyHelper` in `~/.claude/settings.json` | `.claude/agents/*.toml` + `~/.claude/settings.json` |
| **2** | `codex` | `codex exec -c model_reasoning_effort=xhigh -c tool_output_token_limit=500000 -s workspace-write -C WS --skip-git-repo-check -o OUT --json` | Codex CLI provider config | `.codex/config.toml` |

Switch runtimes per command with `--runtime codex` (or set the default globally via `DEFAULT_RUNTIME` in `scripts/runtimes.py`). Both produce the same artifact layout under the run root.

See [`references/runtime-modes.md`](references/runtime-modes.md) for the full side-by-side.

## Layout

```text
codex-subagents-kit/
  SKILL.md                         # Codex-side skill manifest
  bin/
    codex-subagent                 # POSIX wrapper around the Python scripts
  scripts/
    runtimes.py                    # runtime registry + command builders (shared)
    init_subagent_run.py           # init --runtime claude|codex (default claude)
    probe_subagent_runtime.py      # probe --runtime claude|codex
    check_subagent_run.py          # check  (runtime-agnostic; reads manifest)
    run_subagent_task.py           # task   --runtime claude|codex
    run_subagent_regression.py     # regression --runtime claude|codex
  references/
    claude-runtime-notes.md        # Claude Code CLI facts (local evidence)
    codex-runtime-notes.md         # Codex CLI facts (local evidence)
    runtime-modes.md               # claude vs codex side-by-side
    artifact-contract.md           # required files, registry, scorecard, audit
    selection-guide.md             # four-gate + ownership + runtime mode matrix
    decision-matrix.md             # quick 5-layer decision table
    project-agents.md              # .claude/agents/ templates (claude runtime only)
    topology-catalog.md            # research / repair / review formations
    research-swarm-pattern.md      # shared-findings ledger + dedupe + stop rule
    multi-agent-hardening.md       # prompt contract, hot-file rules, reviewer split
    scoring-rubric.md              # Anthropic / OpenAI / Codex methodology rubric
    official-patterns-2026.md      # source map for Anthropic + OpenAI / Codex
    context-efficiency.md          # token / prompt sizing rules
  assets/
    project-agents/                # 4 minimal TOML templates (claude runtime)
      explorer.toml
      reviewer.toml
      verifier.toml
      worker.toml
```

## Quick start

### 1) Bootstrap a run

```bash
# Default (claude runtime)
codex-subagent init --workspace-root . --case my-task

# Mode 2 (codex runtime)
codex-subagent init --workspace-root . --case my-task --runtime codex
```

This writes the standard artifact skeleton under `.workspace/codex-subagents-kit/runs/<run_id>/`:

```
preflight.md
agent-blueprints.md
execution-plan.md
task-registry.md
protocol-audit.md
team-report.md
scorecard.md
manifests/run.json
prompts/
outputs/
logs/
```

### 2) Probe your runtime

```bash
codex-subagent probe --runtime claude --run-root .workspace/codex-subagents-kit/runs/<run_id> --workspace-root .
# or
codex-subagent probe --runtime codex  --run-root .workspace/codex-subagents-kit/runs/<run_id> --workspace-root .
```

Probe writes `manifests/runtime-probe.json` with the four gates and a `recommended_mode` hint. Optionally pass `--write-protocol-audit` to append a note into `protocol-audit.md`.

### 3) Fill in the registry

Edit `task-registry.md` so each row has at least: `Task ID`, `Owner`, `Status`, `Input Path`, `Output Path`, `Acceptance`, `Spawn Reason`.  Contract v2 also requires `Stop Condition`, `Escalation / Fallback`, `Evidence Path`.

Write each child's prompt into `prompts/<task-id>.md`.

### 4) Spawn children

```bash
# Claude runtime
codex-subagent task \
  --run-root .workspace/codex-subagents-kit/runs/<run_id> \
  --prompt-file  .workspace/codex-subagents-kit/runs/<run_id>/prompts/task-a.md \
  --output-file  .workspace/codex-subagents-kit/runs/<run_id>/outputs/task-a.md

# Codex runtime
codex-subagent task --runtime codex \
  --run-root .workspace/codex-subagents-kit/runs/<run_id> \
  --prompt-file  .workspace/codex-subagents-kit/runs/<run_id>/prompts/task-a.md \
  --output-file  .workspace/codex-subagents-kit/runs/<run_id>/outputs/task-a.md
```

Pass `--dry-run` to print the would-be command without executing. Pass `--execute` (only meaningful on `regression`) to actually invoke the runtime.

### 5) Validate

```bash
codex-subagent check --run-root .workspace/codex-subagents-kit/runs/<run_id>
```

`check` is runtime-agnostic; it reads `manifests/run.json` and decides whether your claimed mode (`native-claude-task` / `native-codex-task` / `artifact-orchestrated-swarm` / ...) is consistent with probe evidence.

### 6) Forward / regression test

```bash
# Builds a testbed, drops project-agent templates (claude runtime only), constructs commands.
codex-subagent regression --runtime claude --testbed-root /tmp/csak-regression
codex-subagent regression --runtime codex  --testbed-root /tmp/csak-regression-codex
```

Add `--execute` to actually spawn children (requires `ANTHROPIC_API_KEY` for claude, Codex provider auth for codex).

## Architecture

### Four-gate model

Every decision to spawn lives or dies by four gates:

| Gate | Pass when |
| --- | --- |
| **Product** | The chosen runtime CLI supports the orchestration flags (`--bare` / `--output-format json` for claude; `--output-last-message` / `--json` / `-s` / `-c` for codex). |
| **Session** | The current session exposes live native child-agent tool evidence (Task, spawn_agent, …). |
| **Policy** | The task / risk / user actually allows spawning. |
| **Task** | The candidate has owner / input / output / acceptance / stop condition. |

If Product and Session both pass, you may run in native mode. If only Product passes, you fall back to `artifact-orchestrated-swarm`. If Session evidence is missing for the chosen runtime but config artifacts exist, you fall back to `config-guided-<runtime>-subagents`. Otherwise stay single-controller.

### Ownership shapes

| Shape | Notes |
| --- | --- |
| `single-controller` | Default; cheapest. |
| `manager-with-specialists` | Controller keeps synthesis; specialists do bounded sidecar / verifier / explorer work. Most common multi-agent shape. |
| `handoff-network` | Used when designing external OpenAI / Anthropic SDK blueprints; not native to a Codex session. |
| `research-shared-findings` | Research tasks with shared findings ledger + angle dedupe. |

### Artifact contract (v2)

Each run ships these artifacts. `check` enforces them.

```
preflight.md          — final goal / deliverables / constraints / spawn candidates
agent-blueprints.md   — role / objective / scope per task
execution-plan.md     — chosen mode + ownership + runtime
task-registry.md      — Task ID / Owner / Status / Input / Output / Acceptance /
                         Spawn Reason / Stop Condition / Escalation / Evidence
protocol-audit.md     — claimed mode, four gates, boundaries, evidence, stop / fallback
team-report.md        — final summary + outputs + open risks
scorecard.md          — 8-dimension score (0–2 each)
manifests/
  run.json            — run_id, runtime, required_artifacts, registry columns
  runtime-probe.json  — per-runtime probe facts (claude | codex)
```

## Runtime requirements

- **Python 3.11+** for the scripts.
- **Claude Code CLI** (mode 1) — see `references/claude-runtime-notes.md` for version-specific flags. Default child invocation requires `--bare`; auth needs `ANTHROPIC_API_KEY` or `apiKeyHelper` in `~/.claude/settings.json`. Pass `--no-bare` to fall back to OAuth-only auth.
- **Codex CLI** (mode 2) — `codex --version` ≥ 0.144.x. Provider auth configured via `~/.codex/config.toml` or `OPENAI_API_KEY` / ChatGPT login.

## Choosing between runtimes

| Pick `claude` if … | Pick `codex` if … |
| --- | --- |
| The team standardizes on Claude Code and `.claude/agents/`. | The controller session is itself Codex and you want one CLI surface. |
| You need fine-grained tool gating (`--allowedTools` / `--disallowedTools`). | You need `--output-schema` JSON Schema validation. |
| You want `--bare`-style isolation (no hooks, no auto-memory). | You want `--ephemeral` semantics with `-s workspace-write`. |
| You have `ANTHROPIC_API_KEY` or apiKeyHelper ready. | Provider auth is already configured for Codex. |
| The prompt references Claude-specific tooling (`CLAUDE.md`, `Task` tool). | The prompt references Codex-specific tooling (`codex exec`, JSONL events). |

## Method

This kit synthesizes the same Anthropic and OpenAI / Codex patterns the official guides describe:

- **single-controller first** ([Anthropic](https://www.anthropic.com/engineering/building-effective-agents), [OpenAI](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-agents/))
- **context-centric decomposition** ([Anthropic multi-agent](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them))
- **ownership-first routing** ([OpenAI orchestration](https://developers.openai.com/api/docs/guides/agents/orchestration))
- **summary-only return + evidence path** ([Anthropic research system](https://www.anthropic.com/engineering/multi-agent-research-system))

See [`references/official-patterns-2026.md`](references/official-patterns-2026.md) for the source map.

## License

MIT — see [LICENSE](LICENSE).

## Status

`v0.2.0` (dual-runtime). The previous single-runtime name was `codex-use-claude-subagent`. Migration notes are in [`references/runtime-modes.md`](references/runtime-modes.md).
