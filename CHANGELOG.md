# Changelog

All notable changes to this project are documented in this file.  The format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- `regression` subcommand: forward / regression harness with `--runtime claude|codex`.

## [0.2.0] - 2026-08-30

### Changed

- **Dual-runtime**: added `codex` runtime as mode 2 alongside the default `claude` runtime.  Switch via `--runtime codex` on `init`, `probe`, `task`, `regression`.  Default remains `claude`.
- Skill renamed `codex-use-claude-subagent` → `codex-subagents-kit`.  CLI renamed `bin/claude-subagent` → `bin/codex-subagent`.
- `manifests/run.json` now records an explicit `runtime` field (`"claude"` or `"codex"`) plus `runtime_describe` and `subagent_runtime`.  Existing `subagent_runtime` field kept for backwards reference.
- `check` is runtime-agnostic and reads `runtime` from `manifests/run.json`; native-mode claim check now matches the runtime (`native-claude-task` vs `native-codex-task`).
- `run_root` path renamed from `.workspace/claude-subagent/runs/...` to `.workspace/codex-subagents-kit/runs/...`.
- All scripts renamed:
  - `init_claude_subagent_run.py` → `init_subagent_run.py`
  - `probe_claude_subagent_runtime.py` → `probe_subagent_runtime.py`
  - `run_claude_subagent_task.py` → `run_subagent_task.py`
  - `check_claude_subagent_run.py` → `check_subagent_run.py`
  - `run_claude_subagent_regression.py` → `run_subagent_regression.py`
  - New: `runtimes.py` (runtime registry; shared by all scripts).

### Added

- `references/codex-runtime-notes.md`: local Codex CLI facts, four-gate interpretation, comparison vs claude runtime.
- `references/runtime-modes.md`: side-by-side comparison and migration notes.
- `regression` subcommand: forward-test harness; claude runtime copies `assets/project-agents/*.toml` into the testbed's `.claude/agents/`.

## [0.1.0] - 2026-08-30

### Added

- Initial release as `codex-use-claude-subagent`.
- Claude Code CLI (`claude -p --bare --output-format json`) as the sole subagent runtime.
- `init`, `probe`, `check`, `task` subcommands under `bin/claude-subagent`.
- Artifact contract v2 (`preflight.md`, `agent-blueprints.md`, `execution-plan.md`, `task-registry.md`, `protocol-audit.md`, `team-report.md`, `scorecard.md`, `manifests/run.json`, `manifests/runtime-probe.json`).
- Reference library (`references/*.md`) covering official-patterns, selection guide, decision matrix, project-agents, topology catalog, research swarm pattern, multi-agent hardening, artifact contract, scoring rubric, and Claude runtime notes.
- Four-TOML `assets/project-agents/` template set (`explorer.toml`, `reviewer.toml`, `verifier.toml`, `worker.toml`).
