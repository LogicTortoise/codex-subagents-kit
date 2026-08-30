# Runtime Modes

Side-by-side comparison of the two subagent runtimes supported by this skill.  Both runtimes share the same artifact contract (`prompts/`, `outputs/`, `logs/`, `manifests/`, v2 registry, scorecard).  Only the `manifests/run.json` `runtime` field and the actual child invocation differ.

## At a glance

| Aspect | Mode 1 — `claude` (default) | Mode 2 — `codex` |
| --- | --- | --- |
| CLI executable | `claude` | `codex` |
| Subcommand | `claude -p --bare` | `codex exec` |
| Output format | `--output-format json` (parsed) | `--json` JSONL events + `-o FILE` last message |
| Default child command | `claude -p --bare --output-format json --no-session-persistence --max-budget-usd 5 --allowedTools "Read,Grep,Glob" --disallowedTools "WebFetch,WebSearch" --permission-mode bypassPermissions --add-dir WS --session-id UUID` | `codex exec -c model_reasoning_effort=xhigh -c tool_output_token_limit=500000 -s workspace-write -C WS --skip-git-repo-check -o OUT --json` |
| Prompt in | stdin (trailing `-`) | stdin (trailing `-`) |
| Final assistant text | parsed out of `payload["result"]` or `payload.content[*].text` | read from the `-o` output file (JSONL fallback extracts last assistant message) |
| Auth | `ANTHROPIC_API_KEY` env / `apiKeyHelper` in `~/.claude/settings.json` | Codex provider auth (ChatGPT login, `OPENAI_API_KEY`, or local provider via `--oss`) |
| Sandbox / permissions | `--permission-mode bypassPermissions/plan`, `--allowedTools`, `--disallowedTools` | `-s read-only/workspace-write/danger-full-access` |
| Session persistence | `--no-session-persistence` (default true) | `--ephemeral` (opt-in) |
| Reasoning effort | `--effort low/medium/high/xhigh/max` (empty = inherit env) | `-c model_reasoning_effort=<value>` (default `xhigh` here) |
| Model override | `--model` (empty = inherit env) | `-m, --model` (empty = inherit env) |
| Workspace root | `--add-dir <ws>` (first) | `-C <ws>` |
| Extra dirs | `--add-dir` (repeatable) | `--add-dir` (repeatable) |
| Git repo | not required | `--skip-git-repo-check` (default true) |
| Output schema | not a first-class flag | `--output-schema FILE` |

## How to switch

```bash
# Default (claude)
codex-subagent init    --workspace-root . --case my-task
codex-subagent probe   --run-root .workspace/codex-subagents-kit/runs/<id> --workspace-root .
codex-subagent task    --run-root .workspace/codex-subagents-kit/runs/<id> \
                       --prompt-file .workspace/.../prompts/task-a.md \
                       --output-file .workspace/.../outputs/task-a.md

# Codex
codex-subagent init    --runtime codex --workspace-root . --case my-task
codex-subagent probe   --runtime codex --run-root .workspace/codex-subagents-kit/runs/<id> --workspace-root .
codex-subagent task    --runtime codex --run-root .workspace/codex-subagents-kit/runs/<id> \
                       --prompt-file .workspace/.../prompts/task-a.md \
                       --output-file .workspace/.../outputs/task-a.md

# Check works for both runtimes (runtime-agnostic; reads runtime from manifests/run.json)
codex-subagent check   --run-root .workspace/codex-subagents-kit/runs/<id>
```

## Per-runtime child invocation (canonical)

### claude runtime

```bash
claude -p --bare \
  --output-format json \
  --no-session-persistence \
  --max-budget-usd 5 \
  --allowedTools "Read,Grep,Glob" \
  --disallowedTools "WebFetch,WebSearch" \
  --permission-mode bypassPermissions \
  --add-dir <workspace> \
  --session-id <uuid> \
  [--append-system-prompt-file <file>] \
  -
```

### codex runtime

```bash
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

## Artifact contract (shared)

Both runtimes write to the same artifact layout under `run_root`:

```
run_root/
  preflight.md
  agent-blueprints.md
  execution-plan.md
  task-registry.md        (v2: includes Stop Condition, Escalation / Fallback, Evidence Path)
  protocol-audit.md
  team-report.md
  scorecard.md
  manifests/
    run.json              (records `runtime: claude|codex`)
    runtime-probe.json    (records `runtime` + per-runtime probe facts)
    regression.json       (optional, written by `regression` subcommand)
  prompts/                (one markdown file per child task)
  outputs/                (final assistant text per child task)
  logs/                   (raw child stdout; for codex, JSONL events; for claude, JSON envelope)
```

## Probe differences

`codex-subagent probe` records runtime-specific facts in `manifests/runtime-probe.json`:

- `claude` runtime: `claude_version`, `bare_capable`, `output_format_capable`, `budget_capable`, `tool_allowlist_capable`, `session_id_capable`, `auth_mode.bare_mode_auth_supported`, `bare_help_excerpt`.
- `codex` runtime: `codex_version`, `exec_capable`, `output_last_message_capable`, `json_events_capable`, `sandbox_capable`, `model_reasoning_effort_capable`.

Both share `native_tooling`, `gates.{product_gate, session_gate}`, `config_guided_evidence`, and `assessment.recommended_mode`.

The recommended-mode strings also differ per runtime:

| Runtime | Possible `recommended_mode` values |
| --- | --- |
| `claude` | `native-claude-task`, `artifact-orchestrated-swarm`, `config-guided-claude-subagents`, `single-controller` |
| `codex` | `native-codex-task`, `artifact-orchestrated-swarm`, `config-guided-codex-subagents`, `single-controller` |

`check` reads `manifests/run.json.runtime` to decide which native-mode claim string should be rejected if not backed by probe evidence (`native-claude-task` for the claude runtime, `native-codex-task` for the codex runtime).

## Regression differences

`codex-subagent regression --runtime <claude|codex>` reuses the same testbed scaffolding but uses different forward prompts and only copies `.claude/agents/*.toml` for the claude runtime (Codex does not have an equivalent project-level agent config directory).

| Aspect | `regression --runtime claude` | `regression --runtime codex` |
| --- | --- | --- |
| Copy `assets/project-agents/*.toml` to testbed | yes (`.claude/agents/`) | no |
| Smoke prompt 1 | `smoke-hello` (expects `smoke-ok`) | `smoke-hello` (expects `smoke-ok`) |
| Smoke prompt 2 | `registry-read` (reads `.claude/agents/worker.toml`) | `codex-config-read` (reads `.codex/config.toml` or reports "no codex config") |
| Per-child budget cap | `--max-budget-usd 0.5` | `--tool-output-token-limit 100000` (Codex has no `--max-budget-usd`) |
| `--no-bare` support | yes | n/a (no `--bare` concept) |

## Migration notes (if you used `codex-use-claude-subagent` before)

The previous skill name `codex-use-claude-subagent` is folded into `codex-subagents-kit` with two runtimes.  API-level changes:

| Before (`codex-use-claude-subagent`) | After (`codex-subagents-kit`) |
| --- | --- |
| `bin/claude-subagent` | `bin/codex-subagent` |
| `scripts/init_claude_subagent_run.py` | `scripts/init_subagent_run.py` |
| `scripts/probe_claude_subagent_runtime.py` | `scripts/probe_subagent_runtime.py` |
| `scripts/run_claude_subagent_task.py` | `scripts/run_subagent_task.py` |
| `scripts/check_claude_subagent_run.py` | `scripts/check_subagent_run.py` |
| `scripts/run_claude_subagent_regression.py` | `scripts/run_subagent_regression.py` |
| `run_root` path `.workspace/claude-subagent/runs/...` | `run_root` path `.workspace/codex-subagents-kit/runs/...` |
| `manifests/run.json` field `subagent_runtime: "claude-code-cli"` | `manifests/run.json` field `runtime: "claude"` + `subagent_runtime` retained |
| Default child invocation (claude only) | default still claude; pass `--runtime codex` to switch |
