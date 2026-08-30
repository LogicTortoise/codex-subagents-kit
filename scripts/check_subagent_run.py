#!/usr/bin/env python3
"""Check a subagent run for required artifacts, contract integrity, and closure hygiene.

Runtime-agnostic.  Reads the runtime from `manifests/run.json` and adjusts the
native-mode claim check accordingly (`native-claude-task` for the claude
runtime, `native-codex-task` for the codex runtime).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_FILES = (
    "preflight.md",
    "agent-blueprints.md",
    "execution-plan.md",
    "task-registry.md",
    "protocol-audit.md",
    "team-report.md",
    "scorecard.md",
)

REQUIRED_SUBDIRS = ("prompts", "outputs", "logs", "manifests")
REQUIRED_REGISTRY_COLUMNS_V1 = (
    "Task ID",
    "Owner",
    "Status",
    "Blocked By",
    "Input Path",
    "Output Path",
    "Acceptance",
    "Spawn Reason",
)
REQUIRED_REGISTRY_COLUMNS_V2 = REQUIRED_REGISTRY_COLUMNS_V1 + (
    "Stop Condition",
    "Escalation / Fallback",
    "Evidence Path",
)
PROTOCOL_AUDIT_FIELDS_V2 = (
    "Claimed mode:",
    "Ownership shape:",
    "Product Gate:",
    "Session Gate:",
    "Policy Gate:",
    "Task Gate:",
    "Stop condition:",
    "Fallback:",
    "Registry closed:",
    "Acceptance checked:",
    "Scorecard updated:",
)
SCORECARD_DIMENSIONS_V2 = (
    "Single-controller-first",
    "Ownership-first routing",
    "Context boundary discipline",
    "Runtime honesty",
    "Artifact contract integrity",
    "Stop/fallback discipline",
    "Validation/regression evidence",
    "Audit honesty",
)
COMPLETED_STATUSES = {"done", "completed", "complete", "closed", "passed", "pass"}
OPEN_STATUSES = {"pending", "blocked", "todo", "in_progress", "in-progress", "open"}
NATIVE_MODE_CLAIMS = {
    "claude": "native-claude-task",
    "codex": "native-codex-task",
}


def extract_markdown_table(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines):
        if "|" not in line:
            continue
        if idx + 1 >= len(lines):
            continue
        separator = lines[idx + 1]
        if "|" not in separator or "-" not in separator:
            continue
        header = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows = []
        for row_line in lines[idx + 2 :]:
            if not row_line.strip():
                break
            if "|" not in row_line:
                break
            cells = [cell.strip() for cell in row_line.strip().strip("|").split("|")]
            if len(cells) != len(header):
                continue
            if set(cells) == {"---"}:
                continue
            rows.append(dict(zip(header, cells)))
        return header, rows
    return [], []


def read_text_if_exists(path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json_if_exists(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def infer_workspace_root(run_root, manifest):
    workspace_root = manifest.get("workspace_root")
    if isinstance(workspace_root, str) and workspace_root.strip():
        return Path(workspace_root).resolve()
    try:
        return run_root.parents[3]
    except IndexError:
        return run_root


def normalize_bool_like(value):
    normalized = value.strip().strip("`").strip().lower()
    if normalized in {"true", "yes", "y", "pass", "passed", "complete", "completed", "closed"}:
        return "true"
    if normalized in {"false", "no", "n", "fail", "failed", "open"}:
        return "false"
    if normalized in {"tbd", "", "none"}:
        return "unknown"
    return normalized


def extract_field_value(text, field_name):
    pattern = r"" + re.escape(field_name) + r"\s*`?([^\n`]+?)`?\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def resolve_reference_path(reference, run_root, workspace_root):
    ref = reference.strip().strip("`")
    if not ref or ref.lower() in {"n/a", "none", "tbd"}:
        return None
    candidate = Path(ref)
    if candidate.is_absolute():
        return candidate
    for base in (run_root, workspace_root):
        resolved = (base / candidate).resolve()
        if resolved.exists():
            return resolved
    return (run_root / candidate).resolve()


def scorecard_rows(path):
    return extract_markdown_table(path)


def detect_runtime(manifest):
    explicit = manifest.get("runtime")
    if explicit in {"claude", "codex"}:
        return explicit
    legacy = manifest.get("subagent_runtime")
    if legacy == "codex-cli":
        return "codex"
    return "claude"


def main():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Check a subagent run directory.")
    parser.add_argument("--run-root", required=True, help="Path to the run root.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    run_root = Path(args.run_root).resolve()
    manifest_path = run_root / "manifests" / "run.json"
    manifest = read_json_if_exists(manifest_path)
    contract_version = int(manifest.get("contract_version", 1) or 1)
    runtime = detect_runtime(manifest)
    native_mode_claim = NATIVE_MODE_CLAIMS[runtime]
    workspace_root = infer_workspace_root(run_root, manifest)

    missing_files = [name for name in REQUIRED_FILES if not (run_root / name).exists()]
    missing_subdirs = [name for name in REQUIRED_SUBDIRS if not (run_root / name).is_dir()]
    if not manifest_path.exists():
        missing_files.append("manifests/run.json")

    registry_path = run_root / "task-registry.md"
    protocol_audit_path = run_root / "protocol-audit.md"
    runtime_probe_path = run_root / "manifests" / "runtime-probe.json"
    scorecard_path = run_root / "scorecard.md"

    header, rows = extract_markdown_table(registry_path) if registry_path.exists() else ([], [])
    required_registry_columns = (
        REQUIRED_REGISTRY_COLUMNS_V2 if contract_version >= 2 else REQUIRED_REGISTRY_COLUMNS_V1
    )
    missing_columns = [name for name in required_registry_columns if name not in header]

    pending_rows = [
        row.get("Task ID", "<unknown>")
        for row in rows
        if row.get("Status", "").strip().lower() in OPEN_STATUSES
    ]
    missing_acceptance = [row.get("Task ID", "<unknown>") for row in rows if not row.get("Acceptance", "").strip()]
    missing_spawn_reason = [
        row.get("Task ID", "<unknown>") for row in rows if not row.get("Spawn Reason", "").strip()
    ]
    missing_stop_condition = []
    missing_fallback = []
    missing_evidence_path = []
    missing_output_files = []
    unresolved_evidence_paths = []

    for row in rows:
        task_id = row.get("Task ID", "<unknown>")
        status = row.get("Status", "").strip().lower()
        output_path = row.get("Output Path", "")
        evidence_path = row.get("Evidence Path", "")
        if contract_version >= 2:
            if not row.get("Stop Condition", "").strip():
                missing_stop_condition.append(task_id)
            if not row.get("Escalation / Fallback", "").strip():
                missing_fallback.append(task_id)
        if status in COMPLETED_STATUSES:
            resolved_output = resolve_reference_path(output_path, run_root, workspace_root)
            if resolved_output is None or not resolved_output.exists():
                missing_output_files.append(task_id)
            if contract_version >= 2:
                if not evidence_path.strip():
                    missing_evidence_path.append(task_id)
                else:
                    resolved_evidence = resolve_reference_path(evidence_path, run_root, workspace_root)
                    if resolved_evidence is None or not resolved_evidence.exists():
                        unresolved_evidence_paths.append(task_id)

    protocol_text = read_text_if_exists(protocol_audit_path)
    missing_protocol_fields = []
    protocol_unknown_fields = []
    if contract_version >= 2 and protocol_text:
        for field in PROTOCOL_AUDIT_FIELDS_V2:
            if field not in protocol_text:
                missing_protocol_fields.append(field)
                continue
            value = extract_field_value(protocol_text, field)
            if normalize_bool_like(value) == "unknown":
                protocol_unknown_fields.append(field.rstrip(":"))

    registry_closed_value = normalize_bool_like(extract_field_value(protocol_text, "Registry closed:"))
    acceptance_checked_value = normalize_bool_like(extract_field_value(protocol_text, "Acceptance checked:"))
    scorecard_updated_value = normalize_bool_like(extract_field_value(protocol_text, "Scorecard updated:"))
    claimed_mode = extract_field_value(protocol_text, "Claimed mode:")

    runtime_probe = read_json_if_exists(runtime_probe_path)
    runtime_probe_mode = ""
    runtime_probe_product_gate = None
    runtime_probe_session_gate = None
    if runtime_probe:
        runtime_probe_mode = str(runtime_probe.get("assessment", {}).get("recommended_mode", ""))
        runtime_probe_product_gate = runtime_probe.get("gates", {}).get("product_gate", {}).get("pass")
        runtime_probe_session_gate = runtime_probe.get("gates", {}).get("session_gate", {}).get("pass")

    scorecard_header, scorecard_table_rows = scorecard_rows(scorecard_path) if scorecard_path.exists() else ([], [])
    missing_scorecard_dimensions = []
    blank_scorecard_dimensions = []
    if contract_version >= 2 and scorecard_table_rows:
        seen_dimensions = {row.get("Dimension", "").strip() for row in scorecard_table_rows}
        missing_scorecard_dimensions = [
            dimension for dimension in SCORECARD_DIMENSIONS_V2 if dimension not in seen_dimensions
        ]
        for row in scorecard_table_rows:
            if row.get("Dimension", "").strip() in SCORECARD_DIMENSIONS_V2 and not row.get("Score (0-2)", "").strip():
                blank_scorecard_dimensions.append(row.get("Dimension", "").strip())

    failures = []
    warnings = []

    if not run_root.exists():
        failures.append("run_root_missing")
    if missing_files:
        failures.append("missing_required_files")
    if missing_subdirs:
        failures.append("missing_required_subdirectories")
    if registry_path.exists() and missing_columns:
        failures.append("task_registry_missing_columns")
    if contract_version >= 2 and missing_protocol_fields:
        failures.append("protocol_audit_missing_fields")
    if missing_output_files:
        failures.append("completed_tasks_missing_output_files")
    if unresolved_evidence_paths:
        failures.append("completed_tasks_missing_evidence_files")
    if registry_closed_value == "true" and pending_rows:
        failures.append("audit_registry_closed_conflicts_with_open_tasks")
    if acceptance_checked_value == "true" and (missing_acceptance or missing_output_files):
        failures.append("audit_acceptance_conflicts_with_registry")
    if scorecard_updated_value == "true" and (blank_scorecard_dimensions or missing_scorecard_dimensions):
        failures.append("audit_scorecard_updated_conflicts_with_scorecard")
    if claimed_mode == native_mode_claim:
        if runtime_probe_product_gate is False or runtime_probe_session_gate is False:
            failures.append("native_mode_claim_conflicts_with_runtime_probe")

    if registry_path.exists() and not rows:
        warnings.append("task_registry_has_no_rows")
    if pending_rows:
        warnings.append("task_registry_has_open_tasks")
    if missing_acceptance:
        warnings.append("task_registry_missing_acceptance")
    if missing_spawn_reason:
        warnings.append("task_registry_missing_spawn_reason")
    if contract_version >= 2 and missing_stop_condition:
        warnings.append("task_registry_missing_stop_condition")
    if contract_version >= 2 and missing_fallback:
        warnings.append("task_registry_missing_fallback")
    if contract_version >= 2 and missing_evidence_path:
        warnings.append("completed_tasks_missing_evidence_path")
    if contract_version >= 2 and protocol_unknown_fields:
        warnings.append("protocol_audit_has_tbd_fields")
    if runtime_probe_path.exists() and runtime_probe_mode and claimed_mode and claimed_mode != runtime_probe_mode:
        warnings.append("claimed_mode_differs_from_runtime_probe_recommendation")
    if contract_version >= 2 and missing_scorecard_dimensions:
        warnings.append("scorecard_missing_dimensions")
    if contract_version >= 2 and blank_scorecard_dimensions:
        warnings.append("scorecard_has_blank_scores")

    verdict = "PASS"
    exit_code = 0
    if failures:
        verdict = "FAIL"
        exit_code = 1
    elif warnings:
        verdict = "WARN"

    result = {
        "run_root": str(run_root),
        "workspace_root": str(workspace_root),
        "contract_version": contract_version,
        "runtime": runtime,
        "native_mode_claim": native_mode_claim,
        "verdict": verdict,
        "failures": failures,
        "warnings": warnings,
        "missing_files": missing_files,
        "missing_subdirs": missing_subdirs,
        "task_count": len(rows),
        "pending_tasks": pending_rows,
        "missing_columns": missing_columns,
        "missing_acceptance": missing_acceptance,
        "missing_spawn_reason": missing_spawn_reason,
        "missing_stop_condition": missing_stop_condition,
        "missing_fallback": missing_fallback,
        "missing_evidence_path": missing_evidence_path,
        "missing_output_files": missing_output_files,
        "unresolved_evidence_paths": unresolved_evidence_paths,
        "missing_protocol_fields": missing_protocol_fields,
        "protocol_unknown_fields": protocol_unknown_fields,
        "missing_scorecard_dimensions": missing_scorecard_dimensions,
        "blank_scorecard_dimensions": blank_scorecard_dimensions,
        "claimed_mode": claimed_mode,
        "runtime_probe_mode": runtime_probe_mode,
        "scorecard_header": scorecard_header,
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("VERDICT=" + verdict)
        print("RUN_ROOT=" + str(run_root))
        print("WORKSPACE_ROOT=" + str(workspace_root))
        print("CONTRACT_VERSION=" + str(contract_version))
        print("RUNTIME=" + runtime)
        print("TASK_COUNT=" + str(len(rows)))
        if missing_files:
            print("MISSING_FILES=" + ",".join(missing_files))
        if missing_subdirs:
            print("MISSING_SUBDIRS=" + ",".join(missing_subdirs))
        if missing_columns:
            print("MISSING_COLUMNS=" + ",".join(missing_columns))
        if pending_rows:
            print("PENDING_TASKS=" + ",".join(pending_rows))
        if missing_acceptance:
            print("MISSING_ACCEPTANCE=" + ",".join(missing_acceptance))
        if missing_spawn_reason:
            print("MISSING_SPAWN_REASON=" + ",".join(missing_spawn_reason))
        if missing_stop_condition:
            print("MISSING_STOP_CONDITION=" + ",".join(missing_stop_condition))
        if missing_fallback:
            print("MISSING_FALLBACK=" + ",".join(missing_fallback))
        if missing_evidence_path:
            print("MISSING_EVIDENCE_PATH=" + ",".join(missing_evidence_path))
        if missing_output_files:
            print("MISSING_OUTPUT_FILES=" + ",".join(missing_output_files))
        if unresolved_evidence_paths:
            print("UNRESOLVED_EVIDENCE_FILES=" + ",".join(unresolved_evidence_paths))
        if missing_protocol_fields:
            print("MISSING_PROTOCOL_FIELDS=" + ",".join(missing_protocol_fields))
        if protocol_unknown_fields:
            print("PROTOCOL_TBD_FIELDS=" + ",".join(protocol_unknown_fields))
        if missing_scorecard_dimensions:
            print("MISSING_SCORECARD_DIMENSIONS=" + ",".join(missing_scorecard_dimensions))
        if blank_scorecard_dimensions:
            print("BLANK_SCORECARD_DIMENSIONS=" + ",".join(blank_scorecard_dimensions))
        if claimed_mode:
            print("CLAIMED_MODE=" + claimed_mode)
        if runtime_probe_mode:
            print("RUNTIME_PROBE_MODE=" + runtime_probe_mode)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
