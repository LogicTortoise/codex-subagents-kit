#!/usr/bin/env python3
"""Run a child subagent task from a prompt file.

Default subagent runtime is `claude` (Claude Code CLI in bare mode).  Pass
`--runtime codex` to spawn a child via `codex exec` instead.  Both runtimes
share the same artifact contract (prompt file in, output file + log out).

Default `claude` invocation:

    claude -p --bare --output-format json --no-session-persistence \
        --max-budget-usd N --allowedTools "..." --permission-mode bypassPermissions \
        --add-dir WORKSPACE --session-id UUID [--append-system-prompt-file F] -

Default `codex` invocation:

    codex exec -c model_reasoning_effort=xhigh \
        -s workspace-write -C WORKSPACE --output-last-message OUTPUT --json \
        --skip-git-repo-check -
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtimes import (  # noqa: E402
    CLAUDE_DEFAULT_ALLOWED_TOOLS,
    CLAUDE_DEFAULT_DISALLOWED_TOOLS,
    CLAUDE_DEFAULT_MAX_BUDGET_USD,
    CLAUDE_DEFAULT_PERMISSION_MODE,
    CODEX_DEFAULT_REASONING_EFFORT,
    CODEX_DEFAULT_SANDBOX,
    CODEX_DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT,
    DEFAULT_RUNTIME,
    RUNTIME_CHOICES,
    build_claude_command,
    build_codex_command,
    normalize_runtime,
    parse_claude_json_result,
    resolve_claude_executable,
    resolve_codex_executable,
)


def write_claude_output(output_file, stdout, json_log_file):
    parsed = parse_claude_json_result(stdout)
    if isinstance(parsed.get("result"), str):
        output_file.write_text(parsed["result"], encoding="utf-8")
    else:
        output_file.write_text(
            json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if json_log_file:
        json_log_file.write_text(stdout, encoding="utf-8")


def extract_codex_final_assistant_message(jsonl_text):
    last_text = None
    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        msg = event.get("message")
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") in {"text", "output_text"}:
                    text = block.get("text")
                    if isinstance(text, str):
                        last_text = text
        elif isinstance(content, str):
            last_text = content
    return last_text


def write_codex_output(output_file, raw_stdout, json_log_file):
    if json_log_file:
        json_log_file.write_text(raw_stdout, encoding="utf-8")
    if output_file.exists() and output_file.stat().st_size > 0:
        return
    final_text = extract_codex_final_assistant_message(raw_stdout)
    if final_text:
        output_file.write_text(final_text, encoding="utf-8")
    else:
        output_file.write_text(raw_stdout, encoding="utf-8")


def configure_stdio():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def add_shared_args(parser):
    parser.add_argument("--run-root", required=True, help="Run root for relative paths and logs.")
    parser.add_argument("--workspace-root", help="Workspace root passed to child. Defaults to run_root's grandparent.")
    parser.add_argument("--prompt-file", required=True, help="Prompt file to pass on stdin.")
    parser.add_argument("--output-file", required=True, help="Where the final assistant text should go.")
    parser.add_argument("--add-dir", action="append", default=[], help="Extra --add-dir entries.")
    parser.add_argument("--json-log-file", help="Optional path to dump raw child stdout.")
    parser.add_argument(
        "--runtime",
        choices=RUNTIME_CHOICES,
        default=DEFAULT_RUNTIME,
        help="Subagent runtime: 'claude' (Claude Code CLI, default) or 'codex' (Codex CLI).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the command that would be executed and exit 0.")


def add_claude_args(parser):
    parser.add_argument("--no-bare", action="store_true", help="Skip --bare flag (OAuth-only auth fallback).")
    parser.add_argument("--no-session-persistence", action="store_true", default=True, help="Pass --no-session-persistence. Default true.")
    parser.add_argument("--max-budget-usd", type=float, default=CLAUDE_DEFAULT_MAX_BUDGET_USD, help="Hard USD budget. Default: " + str(CLAUDE_DEFAULT_MAX_BUDGET_USD))
    parser.add_argument("--effort", choices=("low", "medium", "high", "xhigh", "max"), default="", help="Reasoning effort. Empty = inherit env.")
    parser.add_argument("--model", default="", help="Claude model alias/name. Empty = inherit env.")
    parser.add_argument("--allowed-tools", default=CLAUDE_DEFAULT_ALLOWED_TOOLS, help="Comma-separated --allowedTools list.")
    parser.add_argument("--disallowed-tools", default=CLAUDE_DEFAULT_DISALLOWED_TOOLS, help="Comma-separated --disallowedTools list.")
    parser.add_argument("--permission-mode", default=CLAUDE_DEFAULT_PERMISSION_MODE, help="Permission mode. Default 'bypassPermissions'.")
    parser.add_argument("--output-format", choices=("text", "json", "stream-json"), default="json", help="Claude --output-format. Default 'json'.")
    parser.add_argument("--system-prompt-file", help="Optional --system-prompt-file path.")
    parser.add_argument("--append-system-prompt-file", help="Optional --append-system-prompt-file path.")
    parser.add_argument("--settings", help="Optional --settings JSON file or string.")
    parser.add_argument("--session-id", default="", help="UUID for this child run. Auto-generated when empty.")
    parser.add_argument("--claude-executable", help="Override path to the `claude` executable.")


def add_codex_args(parser):
    parser.add_argument("--codex-executable", help="Override path to the `codex` executable.")
    parser.add_argument("--reasoning-effort", default=CODEX_DEFAULT_REASONING_EFFORT, help="Reasoning effort for Codex. Default 'xhigh'.")
    parser.add_argument("--sandbox", default=CODEX_DEFAULT_SANDBOX, choices=("read-only", "workspace-write", "danger-full-access"), help="Codex sandbox mode. Default 'workspace-write'.")
    parser.add_argument("--tool-output-token-limit", type=int, default=CODEX_DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT, help="Per-tool output token budget. Default 500000.")
    parser.add_argument("--skip-git-repo-check", action="store_true", default=True, help="Pass --skip-git-repo-check. Default true.")
    parser.add_argument("--no-skip-git-repo-check", dest="skip_git_repo_check", action="store_false", help="Do NOT pass --skip-git-repo-check.")
    parser.add_argument("--ephemeral", action="store_true", help="Pass --ephemeral so Codex does not persist session files.")
    parser.add_argument("--json-events", action="store_true", default=True, help="Pass --json so Codex emits JSONL events. Default true.")
    parser.add_argument("--no-json-events", dest="json_events", action="store_false", help="Do NOT pass --json; Codex prints plain text.")
    parser.add_argument("--model", default="", help="Override -m/--model for Codex. Empty = inherit env.")


def build_parser(runtime):
    parser = argparse.ArgumentParser(description="Run a subagent task from a prompt file.")
    add_shared_args(parser)
    if runtime == "claude":
        add_claude_args(parser)
    else:
        add_codex_args(parser)
    return parser


def parse_args(argv=None):
    """Two-pass parse: detect --runtime, then re-parse with the right flag set."""
    pre = argparse.ArgumentParser(add_help=False)
    add_shared_args(pre)
    pre_args, _ = pre.parse_known_args(argv)
    runtime = normalize_runtime(pre_args.runtime)
    parser = build_parser(runtime)
    args = parser.parse_args(argv)
    args.runtime = runtime
    return args


def main():
    configure_stdio()
    args = parse_args()

    run_root = Path(args.run_root).resolve()
    prompt_file = Path(args.prompt_file).resolve()
    output_file = Path(args.output_file).resolve()
    json_log_file = Path(args.json_log_file).resolve() if args.json_log_file else None
    if args.workspace_root:
        workspace_root = Path(args.workspace_root).resolve()
    else:
        try:
            workspace_root = run_root.parents[3]
        except IndexError:
            print("Unable to infer workspace root; pass --workspace-root explicitly.", file=sys.stderr)
            return 1

    if not prompt_file.exists():
        print("Prompt file not found: " + str(prompt_file), file=sys.stderr)
        return 1

    if args.runtime == "claude" and not getattr(args, "session_id", ""):
        args.session_id = str(uuid.uuid4())

    prompt_text = prompt_file.read_text(encoding="utf-8")

    if args.runtime == "claude":
        command = build_claude_command(args, prompt_text)
    else:
        command = build_codex_command(args, prompt_text)

    if args.dry_run:
        manifest = {
            "runtime": args.runtime,
            "command": command,
            "command_shell": " ".join(shlex.quote(part) for part in command),
            "cwd": str(workspace_root),
            "prompt_bytes": len(prompt_text.encode("utf-8")),
            "session_id": getattr(args, "session_id", ""),
            "output_file": str(output_file),
            "json_log_file": str(json_log_file) if json_log_file else None,
        }
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0

    output_file.parent.mkdir(parents=True, exist_ok=True)
    if json_log_file:
        json_log_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        if args.runtime == "claude":
            executable = getattr(args, "claude_executable", None) or resolve_claude_executable()
        else:
            executable = getattr(args, "codex_executable", None) or resolve_codex_executable()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    completed = subprocess.run(
        command,
        input=prompt_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        cwd=str(workspace_root),
    )

    if json_log_file:
        json_log_file.write_text(completed.stdout, encoding="utf-8")
    else:
        sys.stdout.write(completed.stdout)

    if completed.stderr:
        sys.stderr.write(completed.stderr)

    if completed.returncode != 0:
        return completed.returncode

    if args.runtime == "claude":
        write_claude_output(output_file, completed.stdout, json_log_file)
    else:
        write_codex_output(output_file, completed.stdout, json_log_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
