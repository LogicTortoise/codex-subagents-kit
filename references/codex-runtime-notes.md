# Codex Runtime Notes

Snapshot date: 2026-08-30

These notes are local evidence for this workstation, not a universal guarantee for every Codex CLI build.  They mirror the role `claude-runtime-notes.md` plays for the claude runtime.

## Observed Local Facts

- `codex --version` returns `codex-cli 0.144.1`.
- `codex exec --help` shows the canonical non-interactive invocation: `codex exec [OPTIONS] [PROMPT]`.
- The prompt is read from stdin when `-` is passed as the final argument; stdin is appended to a positional prompt as a `<stdin>` block.
- Available non-interactive flags that matter for orchestrated subagents:
  - `-c, --config <key=value>` (repeatable; dotted-path overrides)
  - `-m, --model <MODEL>`
  - `-s, --sandbox <read-only|workspace-write|danger-full-access>`
  - `--dangerously-bypass-approvals-and-sandbox`
  - `--dangerously-bypass-hook-trust`
  - `-C, --cd <DIR>` — workspace root
  - `--add-dir <DIR>` (repeatable)
  - `--skip-git-repo-check`
  - `--ephemeral`
  - `--ignore-user-config`
  - `--ignore-rules`
  - `-i, --image <FILE>` (image attachments to initial prompt)
  - `--output-schema <FILE>` (JSON Schema for final response)
  - `-o, --output-last-message <FILE>` — final assistant message written to file
  - `--json` — JSONL events on stdout
  - `--color <always|never|auto>` (default `auto`)
- `codex exec` writes `codex <event>` records as JSONL to stdout when `--json` is set; the final assistant message is written to the path given to `-o/--output-last-message`.
- Provider auth is configured via `~/.codex/config.toml` (and optional project `.codex/config.toml`).  Common values: `OPENAI_API_KEY` env, ChatGPT login, or `local_provider = "lmstudio"|"ollama"` with `--oss`.

## Practical Interpretation

Treat Codex CLI on this machine as:

- product-level support for orchestrated subagents is present (`codex exec` + `--json` + `--output-last-message` + `-s` + `-c`)
- controller-style orchestration is the only honest path today (no live in-session `spawn_agent` tool evidence here)
- file-based planning and audit are stable; same artifact contract as the claude runtime
- the sandbox defaults to `workspace-write`; tighten with `-s read-only` for verifier children
- `-c model_reasoning_effort=xhigh` is the default for this skill, mirroring the claude-runtime default of `inherit env` (Codex doesn't have an exact "inherit" notion — we explicitly set `xhigh` to keep subagent reasoning aligned with controller expectations)
- `--skip-git-repo-check` is on by default in this skill so non-git workspaces still work
- `--ephemeral` is opt-in; without it, Codex may persist session files under `$CODEX_HOME/sessions/`

## Recommended Default

Use the four-gate model (same as claude runtime):

1. **Product Gate**: `codex exec --help` works AND `--output-last-message` / `--json` / `-s` / `-c` are present.
2. **Session Gate**: live in-session spawn tool evidence OR (for orchestrated mode) Codex CLI is installed and auth is configured.
3. **Policy Gate**: this run should actually spawn.
4. **Task Gate**: the task is spawn-worthy.

Decision matrix (Codex runtime):

- Product Gate passes + Session Gate strong → `native-codex-task` (preferred when in-session evidence is real).
- Product Gate passes + Codex CLI auth is configured → `artifact-orchestrated-swarm` (default; spawn `codex exec ...`).
- Product Gate passes + auth missing → fall back to single-controller, or reconfigure Codex provider.
- Product Gate fails → `single-controller` until Codex CLI is installed.

## When to prefer Codex runtime over Claude runtime

- The controller session is itself Codex (so inheriting `codex exec` keeps auth/CLI/version coherent).
- The task description explicitly asks for `codex` / Codex agents / Codex-style JSONL.
- You want `--ephemeral` semantics for one-shot children that must not leave session history.
- You need built-in JSON Schema output validation (`--output-schema`).
- You want a single CLI surface for both controller and subagent (less moving parts in CI/automation).

## When NOT to switch to Codex runtime

- The task is heavily Claude-SDK-shaped (e.g. references `.claude/agents/`, `CLAUDE.md`, `settings.json`).
- You need `--allowedTools` / `--disallowedTools` style fine-grained tool gating (Codex's sandbox is coarser; use `-s read-only` for verifier roles).
- You need `--bare`-style isolation (Codex has no equivalent; closest is `--ephemeral` + `-s workspace-write`).
- The team's tooling around prompt / output artifacts assumes `claude -p` JSON shape.

## Comparison table

| Capability | Claude runtime | Codex runtime |
| --- | --- | --- |
| Non-interactive entrypoint | `claude -p --bare --output-format json` | `codex exec --output-last-message FILE --json` |
| Final answer to file | via `--output-format json` + parsing | direct via `-o FILE` |
| Streaming events | `stream-json` (`--include-partial-messages`) | `--json` JSONL events |
| Reasoning effort override | `--effort low/medium/high/xhigh/max` | `-c model_reasoning_effort=<value>` |
| Model override | `--model <alias-or-name>` | `-m, --model <MODEL>` |
| Hard budget | `--max-budget-usd N` | not a first-class flag; control via `--ephemeral`, sandbox, and explicit prompt budgeting |
| Tool gating | `--allowedTools / --disallowedTools` (granular) | `-s read-only|workspace-write|danger-full-access` (coarse) + `--output-schema` |
| Workspace | `--add-dir` (repeatable) | `-C` (workspace root) + `--add-dir` (extra) |
| Session persistence | `--no-session-persistence` (off by default) | `--ephemeral` (off by default) |
| Auth | `ANTHROPIC_API_KEY` env / `apiKeyHelper` in `~/.claude/settings.json` | Codex CLI provider config (`OPENAI_API_KEY`, ChatGPT login, `--oss` with local provider) |
| Verification role | `--permission-mode plan` (read-only) | `-s read-only` |
| Output schema | not a first-class flag | `--output-schema FILE` |
