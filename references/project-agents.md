# Project Agents (claude runtime)

These project-agent templates are for the **claude runtime only**.  When you run with `--runtime codex`, the equivalent setup is `~/.codex/config.toml` + project `.codex/config.toml`, not `.claude/agents/`.  See `codex-runtime-notes.md` for the Codex side and `runtime-modes.md` for side-by-side comparison.

## Why use `.claude/agents/`

When `config-guided-claude-subagents` wins, project-level `.claude/agents/` is the best place to codify role-shaped behaviour:

- avoid re-explaining role responsibilities on every task
- let project-level roles take precedence over global roles
- pin down explorer / worker / reviewer / verifier boundaries
- keep "who owns synthesis, who is sidecar, who is verifier" stable across runs
- pin stop conditions / approval boundary / summary return contract
- when combined with `codex-subagent task --runtime claude`, `--agents '<json>'` can inline these roles directly

## Recommended templates

In `assets/project-agents/` we provide four minimal TOML templates:

- `explorer.toml`
- `worker.toml`
- `reviewer.toml`
- `verifier.toml`

## Recommended copy target

Copy into the project:

```text
.claude/agents/
  explorer.toml
  worker.toml
  reviewer.toml
  verifier.toml
```

`codex-subagent regression --runtime claude` will do this copy automatically into the testbed.

## Minimal project config

We suggest project `.claude/settings.json` contain at least:

```json
{
  "permissions": {
    "allow": ["Read", "Grep", "Glob"],
    "deny": ["WebFetch"]
  },
  "mcpServers": {}
}
```

Tighten `permissions.deny` for destructive tools as needed (most `Bash` subcommands, `Write`/`Edit`, etc.).

## Design principles

1. explorer is read-only, never writes
2. worker is responsible for editing and fixes
3. reviewer is separate from the implementer
4. verifier only handles tests, regressions, and acceptance evidence
5. controller decides whether hot-file edits run serially
6. default to controller retaining final synthesis; only design handoff when the architecture truly requires specialist ownership
7. every project agent must specify stop condition / escalation condition
8. default return is summary + evidence, not raw long logs

## What belongs where

- `CLAUDE.md`
  - repo norms, build/test/lint, "done" definition, shared collaboration constraints
- `.claude/agents/*.toml` or inline `--agents '<json>'`
  - role boundaries, write permissions, summary return, escalation rules
- task prompt / registry
  - this run's goal, input path, output path, acceptance, time budget

Do not mix these three layers into one giant role description.

## Inline-agent alternative

If you do not want to land `.claude/agents/`, pass `--agents '<json>'` inline when calling `codex-subagent task`:

```bash
codex-subagent task \
  --runtime claude \
  --run-root <run-root> \
  --workspace-root <workspace> \
  --prompt-file <prompt.md> \
  --output-file <output.md> \
  --allowed-tools "Read,Grep,Glob,Bash(limited)" \
  --max-budget-usd 2 \
  --session-id "$(uuidgen)"
```

Put role responsibilities in the prompt header instead of relying on an external agent file.

## Codex runtime equivalent

For the codex runtime, prefer:

- `~/.codex/config.toml` for provider / model defaults
- `.codex/config.toml` for project-level sandbox / approval rules
- `-s read-only` for verifier children
- `-s workspace-write` (default) for executor children
- `--ephemeral` for one-shot children that must not leave session history
- `--output-schema <file>` if you want to validate the final assistant message shape

See `references/codex-runtime-notes.md` and `references/runtime-modes.md` for the full picture.
