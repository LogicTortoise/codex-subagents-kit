# Multi-Agent Hardening

## Core Rules

1. Keep prompts narrow.
2. Keep outputs file-based.
3. Keep ownership explicit.
4. Keep acceptance testable.
5. Keep claims honest.
6. Separate implementer and reviewer when quality matters.
7. Keep raw noise local; return summaries plus evidence pointers.
8. Every loop needs stop conditions and fallback.

## Child Run Prompt Contract

Every child prompt should contain:

- `task_id`
- objective
- allowed scope
- forbidden scope
- recommended tools / source bias
- input path
- output path
- acceptance
- stop condition
- escalation condition
- summary return contract

Example skeleton:

```text
Task ID: RSRCH-01
Objective: Compare two existing files and summarize the differences.
Allowed scope: Read-only analysis of the listed files.
Forbidden scope: Do not edit source files. Do not widen scope.
Recommended tools: shell grep + official docs only.
Input path: docs/a.md, docs/b.md
Output path: .workspace/codex-subagents-kit/runs/<run_id>/outputs/rsrch-01.md
Acceptance: Output contains a concise diff summary and 3 concrete recommendations.
Stop condition: Finish after writing the output file.
Escalation condition: If either file is missing or the task depends on unlisted files, stop and report the blocker.
Summary return contract: Return findings, cited evidence paths, open questions; do not paste raw logs unless asked.
```

## File Boundary Rules

- Do not spawn two child runs that edit the same hot file at the same time.
- Prefer analysis-first child runs and controller-owned merge steps.
- When edits are unavoidable, partition files, use worktrees, or time-slice the runs.

## Summary-Only Return Rules

- Default child output shape:
  1. `summary`
  2. `evidence`
  3. `open_questions`
  4. `recommended_next_step`
- Do not dump raw tool output into the main thread unless it is itself the evidence requested.
- For search / research tasks, prefer a structured findings file plus source links over transcript-style notes.

## Shared Findings Rules

- Research tasks should maintain one shared findings ledger or registry.
- Explorers must divide angles explicitly: topic, region, source type, time window, or subsystem.
- Before appending findings, check whether the same event / issue was already recorded.
- If two consecutive rounds add no materially new findings, stop or escalate.

## Stop Condition Patterns

Pick at least one, preferably two:

- max rounds
- time budget
- no-new-findings threshold
- verifier says good enough
- fallback to human / controller best-effort merge

## Reviewer Separation

- The model or agent that implemented a change should not be the only reviewer.
- If a task requires quality confidence, add a dedicated reviewer/verifier step.
- For PR-style flows, security review and docs review may be split from code review.

## Honesty Rules

- `native-claude-task` means the current runtime truly provides native child-agent behavior.
- `config-guided-claude-subagents` means the controller is configuring Claude Code-native project structures (`.claude/agents/`, `settings.json`, `CLAUDE.md`) for future/indirect subagent execution.
- `artifact-orchestrated-swarm` means the controller is orchestrating child `claude -p --bare` runs.
- `handoff-network` in this skill usually means an external architecture blueprint (Anthropic Agent SDK or OpenAI Agents SDK), not proof that the current Codex session natively supports handoff.
- A feature flag alone is not proof of runtime capability.
- A planned child run is not a completed child run.

## Completion Rules

Do not call the run complete until:

1. registry statuses are updated
2. outputs are present
3. acceptance was checked
4. audit notes reflect deviations
5. scorecard was updated
6. stop / fallback outcomes were recorded
