#!/usr/bin/env python3
"""Initialize a standard subagent run directory.

Default subagent runtime is `claude` (Claude Code CLI in bare mode).  Pass
`--runtime codex` to record a run that will be executed by Codex CLI in
`codex exec` mode instead.  Both runtimes share the same artifact contract;
only the `manifests/run.json` `runtime` field and a few audit template
strings differ.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtimes import DEFAULT_RUNTIME, RUNTIME_CHOICES, normalize_runtime, runtime_describe  # noqa: E402


ARTIFACTS = (
    "preflight.md",
    "agent-blueprints.md",
    "execution-plan.md",
    "task-registry.md",
    "protocol-audit.md",
    "team-report.md",
    "scorecard.md",
)

SUBDIRS = ("prompts", "outputs", "logs", "manifests")
CONTRACT_VERSION = 2
REGISTRY_COLUMNS = (
    "Task ID",
    "Owner",
    "Status",
    "Blocked By",
    "Input Path",
    "Output Path",
    "Acceptance",
    "Spawn Reason",
    "Stop Condition",
    "Escalation / Fallback",
    "Evidence Path",
)
SCORECARD_DIMENSIONS = (
    ("Single-controller-first", "official"),
    ("Ownership-first routing", "official"),
    ("Context boundary discipline", "official"),
    ("Runtime honesty", "official"),
    ("Artifact contract integrity", "engineering"),
    ("Stop/fallback discipline", "official"),
    ("Validation/regression evidence", "official+engineering"),
    ("Audit honesty", "official"),
)


def utc_now():
    return datetime.now(timezone.utc)


def configure_stdio():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def make_run_id(case_name):
    stamp = utc_now().strftime("%Y%m%d-%H%M%S")
    slug = "-".join(case_name.strip().lower().split())
    return stamp + "-" + slug


def write_if_missing(path, content):
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def build_preflight(run_id, run_root, workspace_root, case_name, runtime):
    desc = runtime_describe(runtime)
    return (
        "# Preflight\n\n"
        "- Run ID: `" + run_id + "`\n"
        "- Run Root: `" + str(run_root) + "`\n"
        "- Workspace Root: `" + str(workspace_root) + "`\n"
        "- Case: `" + case_name + "`\n"
        "- Runtime: `" + runtime + "` (" + desc["label"] + ")\n"
        "- Child invocation: `" + desc["invocation"] + "`\n\n"
        "## Final Goal\n\n"
        "- [ ] Fill in the final outcome this run should achieve.\n\n"
        "## Deliverables\n\n"
        "- [ ] List the concrete files or outcomes required.\n\n"
        "## Constraints\n\n"
        "- [ ] Record file boundaries, safety limits, and time constraints.\n"
        "- [ ] Record per-child budgets and tool restrictions.\n\n"
        "## Success Criteria\n\n"
        "- [ ] Define what counts as done.\n\n"
        "## Spawn Candidates\n\n"
        "| Task ID | Candidate | Why Spawn | Inputs | Outputs | Acceptance |\n"
        "| --- | --- | --- | --- | --- | --- |\n\n"
        "## Tasks Not Worth Spawning\n\n"
        "| Task | Why Keep With Controller |\n"
        "| --- | --- |\n"
    )


def build_blueprints(run_id, run_root):
    return (
        "# Agent Blueprints\n\n"
        "- Run ID: `" + run_id + "`\n"
        "- Run Root: `" + str(run_root) + "`\n\n"
        "| Task ID | Role | Objective | Allowed Scope | Forbidden Scope | Input Path | Output Path | Acceptance |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )


def build_execution_plan(run_id, run_root, runtime):
    desc = runtime_describe(runtime)
    return (
        "# Execution Plan\n\n"
        "- Run ID: `" + run_id + "`\n"
        "- Run Root: `" + str(run_root) + "`\n"
        "- Runtime: `" + runtime + "` (" + desc["label"] + ")\n\n"
        "## Chosen Mode\n\n"
        "- Mode: `TBD`\n"
        "- Ownership shape: `TBD`\n"
        "- Runtime version: `TBD`\n"
        "- Bare / non-interactive mode: `TBD`\n"
        "- Native Task tool evidence: `TBD`\n"
        "- Preferred mode when proven: `native-claude-task` (claude runtime) or `native-codex-task` (codex runtime)\n"
        "- Artifact path: `artifact-orchestrated-swarm` (default `" + desc["invocation"] + "`)\n"
        "- Controller-owned merge: `required`\n\n"
        "## Phases\n\n"
        "1. Preflight and scope lock\n"
        "2. Spawn gate and task registry\n"
        "3. Child execution or controller execution\n"
        "4. Merge and acceptance\n"
        "5. Audit and final report\n\n"
        "## Checkpoints\n\n"
        "- [ ] Registry initialized\n"
        "- [ ] Outputs assigned\n"
        "- [ ] Acceptance rules written\n"
        "- [ ] Stop / fallback rules written\n"
        "- [ ] Audit updated\n"
    )


def build_registry(run_id, run_root):
    return (
        "# Task Registry\n\n"
        "- Run ID: `" + run_id + "`\n"
        "- Run Root: `" + str(run_root) + "`\n"
        "- Contract Version: `v" + str(CONTRACT_VERSION) + "`\n\n"
        "| Task ID | Owner | Status | Blocked By | Input Path | Output Path | Acceptance | Spawn Reason | Stop Condition | Escalation / Fallback | Evidence Path |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )


def build_protocol_audit(run_id, run_root, runtime):
    desc = runtime_describe(runtime)
    first_word = desc["invocation"].split()[0]
    return (
        "# Protocol Audit\n\n"
        "- Run ID: `" + run_id + "`\n"
        "- Run Root: `" + str(run_root) + "`\n"
        "- Runtime: `" + runtime + "`\n"
        "- Contract Version: `v" + str(CONTRACT_VERSION) + "`\n\n"
        "## Runtime Mode\n\n"
        "- Claimed mode: `TBD`\n"
        "- Ownership shape: `TBD`\n"
        "- Runtime version: `TBD`\n"
        "- Native Task tool used: `TBD`\n"
        "- Native tool evidence: `TBD`\n"
        "- Child `" + first_word + "` used: `TBD`\n\n"
        "## Four Gates\n\n"
        "- Product Gate: `TBD`\n"
        "- Session Gate: `TBD`\n"
        "- Policy Gate: `TBD`\n"
        "- Task Gate: `TBD`\n\n"
        "## Boundaries\n\n"
        "- `CLAUDE.md` boundary: `TBD`\n"
        "- `.claude/agents/` boundary: `TBD`\n"
        "- Tools / MCP boundary: `TBD`\n"
        "- Runtime state boundary: `TBD`\n"
        "- Model override: `inherit`\n\n"
        "## Evidence\n\n"
        "- Capability probe:\n"
        "- Native tool probe:\n"
        "- Child run evidence:\n"
        "- Regression evidence:\n"
        "- Deviation log:\n\n"
        "## Stop / Fallback\n\n"
        "- Stop condition: `TBD`\n"
        "- Fallback: `TBD`\n"
        "- Escalation condition: `TBD`\n\n"
        "## Final Assessment\n\n"
        "- Registry closed: `TBD`\n"
        "- Acceptance checked: `TBD`\n"
        "- Scorecard updated: `TBD`\n"
        "- Remaining gaps:\n"
    )


def build_team_report(run_id, run_root):
    return (
        "# Team Report\n\n"
        "- Run ID: `" + run_id + "`\n"
        "- Run Root: `" + str(run_root) + "`\n\n"
        "## Summary\n\n"
        "- Mode:\n"
        "- Goal:\n"
        "- Result:\n\n"
        "## Outputs\n\n"
        "- List final artifacts and business outputs here.\n\n"
        "## Open Risks\n\n"
        "- List remaining risks or follow-ups here.\n"
    )


def build_scorecard(run_id, run_root):
    rows = "\n".join(
        "| " + dim + " | " + src + " |  |  |  |"
        for dim, src in SCORECARD_DIMENSIONS
    )
    return (
        "# Scorecard\n\n"
        "- Run ID: `" + run_id + "`\n"
        "- Run Root: `" + str(run_root) + "`\n"
        "- Contract Version: `v" + str(CONTRACT_VERSION) + "`\n\n"
        "| Dimension | Source | Score (0-2) | Evidence | Notes |\n"
        "| --- | --- | --- | --- | --- |\n"
        + rows + "\n\n"
        "## Notes\n\n"
        "- Token efficiency observations:\n"
        "- What improved vs baseline:\n"
        "- Remaining gaps:\n"
    )


def main():
    configure_stdio()
    parser = argparse.ArgumentParser(description="Initialize a subagent run directory.")
    parser.add_argument("--workspace-root", default=".", help="Workspace root that owns the run.")
    parser.add_argument("--case", required=True, help="Short case name used in the run id.")
    parser.add_argument("--run-id", help="Explicit run id. Default: timestamp + case slug.")
    parser.add_argument(
        "--runtime",
        choices=RUNTIME_CHOICES,
        default=DEFAULT_RUNTIME,
        help="Subagent runtime: 'claude' (Claude Code CLI, default) or 'codex' (Codex CLI).",
    )
    args = parser.parse_args()

    runtime = normalize_runtime(args.runtime)

    workspace_root = Path(args.workspace_root).resolve()
    run_id = args.run_id or make_run_id(args.case)
    run_root = workspace_root / ".workspace" / "codex-subagents-kit" / "runs" / run_id
    run_root.mkdir(parents=True, exist_ok=True)

    for subdir in SUBDIRS:
        (run_root / subdir).mkdir(parents=True, exist_ok=True)

    write_if_missing(
        run_root / "preflight.md",
        build_preflight(run_id, run_root, workspace_root, args.case, runtime),
    )
    write_if_missing(run_root / "agent-blueprints.md", build_blueprints(run_id, run_root))
    write_if_missing(
        run_root / "execution-plan.md",
        build_execution_plan(run_id, run_root, runtime),
    )
    write_if_missing(run_root / "task-registry.md", build_registry(run_id, run_root))
    write_if_missing(
        run_root / "protocol-audit.md",
        build_protocol_audit(run_id, run_root, runtime),
    )
    write_if_missing(run_root / "team-report.md", build_team_report(run_id, run_root))
    write_if_missing(run_root / "scorecard.md", build_scorecard(run_id, run_root))

    manifest = {
        "run_id": run_id,
        "contract_version": CONTRACT_VERSION,
        "workspace_root": str(workspace_root),
        "run_root": str(run_root),
        "case_name": args.case,
        "runtime": runtime,
        "runtime_describe": runtime_describe(runtime),
        "subagent_runtime": (
            "claude-code-cli" if runtime == "claude" else "codex-cli"
        ),
        "created_at_utc": utc_now().isoformat(),
        "required_artifacts": list(ARTIFACTS),
        "subdirectories": list(SUBDIRS),
        "task_registry_required_columns": list(REGISTRY_COLUMNS),
        "scorecard_dimensions": [
            {"dimension": dim, "source": src} for dim, src in SCORECARD_DIMENSIONS
        ],
    }
    (run_root / "manifests" / "run.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("RUN_ID=" + run_id)
    print("RUN_ROOT=" + str(run_root))
    print("RUNTIME=" + runtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
