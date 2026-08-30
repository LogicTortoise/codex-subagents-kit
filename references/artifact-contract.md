# Artifact Contract

Current contract version: `v2`

## Required run artifacts

- `preflight.md`
- `agent-blueprints.md`
- `execution-plan.md`
- `task-registry.md`
- `protocol-audit.md`
- `team-report.md`
- `scorecard.md`
- `manifests/run.json`

## Recommended runtime evidence

When a run discusses `native-claude-task`, `config-guided-claude-subagents`, or `artifact-orchestrated-swarm`, it should also keep:

- `manifests/runtime-probe.json`
- one or more prompt files under `prompts/`
- one or more output files under `outputs/`
- optional JSON event logs under `logs/`

## Registry minimum columns

- `Task ID`
- `Owner`
- `Status`
- `Blocked By`
- `Input Path`
- `Output Path`
- `Acceptance`
- `Spawn Reason`
- `Stop Condition`
- `Escalation / Fallback`
- `Evidence Path`

Compatibility rule: keep the original eight column names unchanged; only append new columns.

## Protocol audit minimum fields and sections

- chosen mode
- ownership shape
- four-gate result
- native / config-guided / artifact evidence
- child `claude -p --bare` usage
- `CLAUDE.md` / tools / MCP / runtime-state boundary notes
- stop condition
- fallback / escalation
- deviations and downgrades
- closure state
- scorecard update state

Minimal section checklist:

1. `Runtime Mode`
2. `Four Gates`
3. `Boundaries`
4. `Evidence`
5. `Stop / Fallback`
6. `Final Assessment`

## Runtime probe minimum expectations

If `runtime-probe.json` exists, it should include:

- `claude_version`
- `native_tooling`
- `gates.product_gate`
- `gates.session_gate`
- `config_guided_evidence`
- `exec_capability` (per-flag presence: `--bare`, `--output-format`, `--max-budget-usd`, `--allowedTools`, `--session-id`)
- `auth_mode.bare_mode_auth_supported`
- `assessment.recommended_mode`
- command output snapshots for `claude --version` / `claude --help` / `claude -p --help`

CLI capability alone is not sufficient proof of current-session native child-agent capability.

## Scorecard dimensions

- Single-controller-first
- Ownership-first routing
- Context boundary discipline
- Runtime honesty
- Artifact contract integrity
- Stop/fallback discipline
- Validation/regression evidence
- Audit honesty

Recommended scoring scale: `0-2` per dimension.

## Completion rule

Do not call the run complete until:

1. registry is updated
2. expected outputs exist
3. acceptance is checked
4. protocol-audit reflects deviations
5. scorecard is updated
6. stop / fallback outcomes are recorded
7. completed tasks have resolvable `Output Path`
8. completed tasks have at least one resolvable `Evidence Path` or an explicit why-no-evidence note
