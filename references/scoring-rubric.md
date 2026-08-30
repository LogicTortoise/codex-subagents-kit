# Scoring Rubric

Use this rubric when running forward-tests / regression on `codex-subagents-kit`.

## Two-layer structure

- **Layer A — official-method mapping**
  - Derived from the local bridges:
    - `references/official-patterns-2026.md`
    - `references/research-swarm-pattern.md`
- **Layer B — engineering closure**
  - Local implementation discipline needed to make the skill honest, testable, and auditable in Codex

Recommended total: **24**

- Layer A: `8 × 2 = 16`
- Layer B: `4 × 2 = 8`

## Layer A — official-method mapping (0-2 each)

1. `Single-controller-first`
   - 0: defaults to swarm without checking simpler path
   - 1: mentions a simpler path but does not justify the upgrade clearly
   - 2: compares the simpler path first, then justifies the chosen topology
2. `Ownership-first routing`
   - 0: no final synthesis owner
   - 1: owner is named but specialist/verifier boundaries are blurred
   - 2: controller, sidecar, and verifier boundaries are explicit
3. `Context boundary discipline`
   - 0: title-centric or overlapping splits
   - 1: some boundary thinking, but still high overlap
   - 2: decomposition follows file, evidence, or angle boundaries with low overlap
4. `Generator-verifier overlay discipline`
   - 0: verifier is treated as the whole architecture or rubric is missing
   - 1: verifier exists but the rubric is vague
   - 2: verifier is clearly an overlay with explicit acceptance/rubric
5. `Research-swarm orthogonality`
   - 0: explorers overlap heavily
   - 1: angle split or shared findings exists, but not both
   - 2: angle map, shared findings, and dedupe are all explicit
6. `Boundary clarity`
   - 0: `CLAUDE.md`, tools/MCP, and runtime state are mixed
   - 1: boundaries are mentioned but not assigned clearly
   - 2: each layer is assigned clearly
7. `Stop/fallback/eval discipline`
   - 0: no stop condition and no fallback
   - 1: only one stop lever or a vague fallback
   - 2: at least two stop levers plus fallback or verifier/grader plan
8. `Summary-only return`
   - 0: raw logs flood the main thread
   - 1: summaries are requested but boundaries are vague
   - 2: summary-only / evidence-dense return is explicit and long outputs stay on disk

## Layer B — engineering closure (0-2 each)

9. `Runtime honesty`
   - 0: claims native subagents without enough evidence
   - 1: mostly honest but gate evidence is incomplete
   - 2: product/session/policy/task gate story is explicit and honest
10. `Artifact contract integrity`
   - 0: missing critical artifacts or task-contract fields
   - 1: artifacts exist but are incomplete
   - 2: artifacts, fields, and evidence pointers are complete enough for checking
11. `Closure robustness`
   - 0: pending tasks remain or outputs are missing
   - 1: most statuses are closed but closure/gaps are unclear
   - 2: statuses, outputs, evidence, and remaining gaps all line up
12. `Auditability`
   - 0: conclusions cannot be traced back to evidence
   - 1: partial traceability only
   - 2: claims, evidence paths, scorecard, and team report are mutually traceable

## Prompt coverage recommendation

Use **6-10 real prompts** and cover at least:

1. single-controller
2. manager-with-specialists
3. research-swarm
4. config-guided-claude-subagents
5. artifact-orchestrated-swarm
6. generator-verifier overlay
7. `CLAUDE.md` / tools / MCP / runtime-state boundaries
8. stop conditions / fallback
9. one negative case that should stay simple

## Release gate recommendation

Recommended thresholds before updating the skill body:

- total score `>= 20/24`
- official-method layer `>= 13/16`
- none of these dimensions may score `0`:
  - `Single-controller-first`
  - `Stop/fallback/eval discipline`
  - `Runtime honesty`
  - `Artifact contract integrity`
