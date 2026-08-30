#!/usr/bin/env python3
"""Regression/forward-test harness for codex-subagents-kit.

Builds a sandbox testbed, drops project-agent templates into `.claude/agents/`
(for claude runtime), constructs run artifacts, and (in dry-run mode) validates
the `claude -p --bare` or `codex exec` command shape without burning budget.

Use `--execute` to actually spawn child runs. Both runtimes need their normal
auth setup:

- claude: ANTHROPIC_API_KEY in env, or apiKeyHelper in ~/.claude/settings.json
- codex: provider auth configured in Codex CLI config
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtimes import DEFAULT_RUNTIME, RUNTIME_CHOICES, normalize_runtime  # noqa: E402


def configure_stdio():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path, payload):
    write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def ensure_testbed_claude_agents(skill_root, testbed_root):
    copied = []
    source_dir = skill_root / "assets" / "project-agents"
    target_dir = testbed_root / ".claude" / "agents"
    target_dir.mkdir(parents=True, exist_ok=True)
    if not source_dir.exists():
        return copied
    for source in sorted(source_dir.glob("*.toml")):
        target = target_dir / source.name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append(str(target.relative_to(testbed_root)))
    return copied


FORWARD_PROMPTS_CLAUDE = (
    (
        "smoke-hello",
        "You are a Claude subagent smoke test. Reply with EXACTLY: smoke-ok. No other text.",
    ),
    (
        "registry-read",
        "Read .claude/agents/worker.toml in the testbed and report its role description verbatim.",
    ),
)

FORWARD_PROMPTS_CODEX = (
    (
        "smoke-hello",
        "You are a Codex subagent smoke test. Reply with EXACTLY: smoke-ok. No other text.",
    ),
    (
        "codex-config-read",
        "If a .codex/config.toml file exists in the testbed, report its contents verbatim. Otherwise say 'no codex config'.",
    ),
)


def main():
    configure_stdio()
    parser = argparse.ArgumentParser(description="Run forward/regression tests for codex-subagents-kit.")
    parser.add_argument(
        "--skill-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Path to the skill root. Default: parent of this script.",
    )
    parser.add_argument(
        "--testbed-root",
        required=True,
        help="Where to build the sandbox testbed.",
    )
    parser.add_argument(
        "--runtime",
        choices=RUNTIME_CHOICES,
        default=DEFAULT_RUNTIME,
        help="Subagent runtime to test. Default: claude.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually spawn child subagent runs. Default: dry-run only.",
    )
    parser.add_argument(
        "--no-bare",
        action="store_true",
        help="Claude-only: pass --no-bare to spawned children (OAuth-only auth).",
    )
    parser.add_argument(
        "--max-budget-usd",
        type=float,
        default=0.5,
        help="Per-child budget cap when --execute is set. Default 0.5.",
    )
    args = parser.parse_args()

    runtime = normalize_runtime(args.runtime)
    skill_root = Path(args.skill_root).resolve()
    testbed_root = Path(args.testbed_root).resolve()
    testbed_root.mkdir(parents=True, exist_ok=True)
    copied_agents = ensure_testbed_claude_agents(skill_root, testbed_root) if runtime == "claude" else []

    run_root = testbed_root / ".workspace" / "codex-subagents-kit" / "regression"
    if run_root.exists():
        shutil.rmtree(run_root)
    for subdir in ("prompts", "outputs", "logs", "manifests"):
        (run_root / subdir).mkdir(parents=True, exist_ok=True)

    prompts = FORWARD_PROMPTS_CLAUDE if runtime == "claude" else FORWARD_PROMPTS_CODEX
    results = []
    for task_id, prompt in prompts:
        prompt_path = run_root / "prompts" / (task_id + ".md")
        output_path = run_root / "outputs" / (task_id + ".md")
        log_path = run_root / "logs" / (task_id + ".json")
        prompt_path.write_text(prompt, encoding="utf-8")

        cmd = [
            sys.executable,
            str(skill_root / "scripts" / "run_subagent_task.py"),
            "--run-root", str(run_root),
            "--workspace-root", str(testbed_root),
            "--prompt-file", str(prompt_path),
            "--output-file", str(output_path),
            "--json-log-file", str(log_path),
            "--runtime", runtime,
        ]
        if runtime == "claude":
            cmd.extend(["--max-budget-usd", str(args.max_budget_usd)])
            if args.no_bare:
                cmd.append("--no-bare")
        else:
            cmd.extend(["--tool-output-token-limit", "100000"])

        if args.execute:
            completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        else:
            cmd.append("--dry-run")
            completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

        record = {
            "task_id": task_id,
            "prompt_path": str(prompt_path),
            "output_path": str(output_path),
            "log_path": str(log_path),
            "exit_code": completed.returncode,
            "executed": args.execute,
            "runtime": runtime,
        }
        if not args.execute:
            try:
                record["dry_run_command"] = json.loads(completed.stdout).get("command")
            except json.JSONDecodeError:
                record["dry_run_command"] = completed.stdout.strip()
        else:
            record["output_present"] = output_path.exists() and output_path.stat().st_size > 0
        if completed.stderr:
            record["stderr_tail"] = completed.stderr[-400:]
        results.append(record)

    summary = {
        "probed_at_utc": utc_now(),
        "skill_root": str(skill_root),
        "testbed_root": str(testbed_root),
        "runtime": runtime,
        "copied_agents": copied_agents,
        "executed": args.execute,
        "results": results,
    }
    write_json(run_root / "manifests" / "regression.json", summary)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    failed = [r for r in results if r["exit_code"] != 0]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
