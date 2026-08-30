# Claude Runtime Notes

Snapshot date: 2026-08-30

These notes are local evidence for this workstation, not a universal guarantee for every Claude Code build.

## Observed Local Facts

- `claude --version` returns `2.1.251 (Claude Code)`.
- `claude --help` and `claude -p --help` both work; the canonical non-interactive invocation is `claude -p --bare --output-format json -`.
- `--bare` is documented as: skips hooks / LSP / plugin sync / attribution / auto-memory / background prefetches / keychain reads / CLAUDE.md auto-discovery. Sets `CLAUDE_CODE_SIMPLE=1`. Auth is strictly `ANTHROPIC_API_KEY` env or `apiKeyHelper` via `--settings` (OAuth and keychain are never read in bare mode).
- Available non-interactive flags that matter for orchestrated subagents:
  - `--bare`
  - `--output-format {text,json,stream-json}`
  - `--no-session-persistence`
  - 
  - `--max-budget-usd N` (only with `--print`/`-p`)
  - `--allowedTools / --allowed-tools`
  - `--disallowedTools / --disallowed-tools`
  - `--add-dir <dir>` (repeatable)
  - `--session-id <uuid>`
  - `--system-prompt` / `--system-prompt-file`
  - `--append-system-prompt` / `--append-system-prompt-file`
  - `--settings <file-or-json>`
  - `--mcp-config <files...>`
  - `--agents <json>` (inline custom agents)
  - `--plugin-dir <path>` / `--plugin-url <url>`
  - `--permission-mode {acceptEdits,auto,bypassPermissions,manual,dontAsk,plan}`
  - `--effort {low,medium,high,xhigh,max}`
  - `--model <alias-or-name>`
  - `--include-partial-messages` (with `--print` + `stream-json`)
  - `--forward-subagent-text` (with `--print` + `stream-json`)
- Current session auth: **no `ANTHROPIC_API_KEY` in env, likely OAuth**. So `--bare` mode will fail auth until the user provides `ANTHROPIC_API_KEY` or sets up `apiKeyHelper` in `~/.claude/settings.json`. Workaround for orchestrated spawn today: pass `--no-bare` to fall back to default Claude Code mode.
- `~/.claude/agents/` exists; no project-level `.claude/agents/` observed in current workspace.
- No project `settings.json` observed in the probed workspace.
- 2026-08-30 runtime probe records that the Codex-side session does NOT expose a live `Task` tool to the underlying model (controller is acting as orchestrator, not as a Claude Code Task caller). Spawn path is artifact-orchestrated, not native-claude-task.

## Practical Interpretation

Treat Claude Code on this machine as:

- product-level support for orchestrated subagents is present (`--bare` + `--output-format json` + budget / turn caps)
- controller-style orchestration is the only honest path today (no live `Task` tool evidence)
- file-based planning and audit are stable; same artifact contract as before
- `claude -p --bare` child runs are usable **once auth is wired** (API key or apiKeyHelper)
- `--no-bare` is a fallback for OAuth-only setups; loses auto-discovery isolation
- `CLAUDE.md` + `.claude/agents/` + `settings.json` are the config-guided defaults

## Recommended Default

Use the four-gate model:

1. **Product Gate**: `claude --version` works AND `--bare` is present in help.
2. **Session Gate**: live in-session `Task` tool evidence OR (for orchestrated mode) bare-mode auth path is available.
3. **Policy Gate**: this run should actually spawn.
4. **Task Gate**: the task is spawn-worthy.

Decision matrix:

- Product Gate passes + Session Gate strong + bare-auth supported → `native-claude-task` (preferred when in-session evidence is real).
- Product Gate passes + bare-auth supported → `artifact-orchestrated-swarm` (default; spawn `claude -p --bare`).
- Product Gate passes + only OAuth (no API key) → `artifact-orchestrated-swarm` with `--no-bare`; OR set up apiKeyHelper for `--bare`.
- Product Gate passes + no config artifacts → `config-guided-claude-subagents` first; only spawn if config is enough.
- Product Gate fails → `single-controller`.
