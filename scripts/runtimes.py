"""Subagent runtime registry.

Each runtime is a small description + helpers for one of the supported child
subagent executors. The default is `claude` (Claude Code CLI in bare mode);
the alternative is `codex` (Codex CLI in `codex exec` mode).

Runtimes differ in three places only:
1. how to find the executable on PATH,
2. how to build the argv list that spawns one child,
3. how to parse the child's stdout / stderr into the on-disk output artifact.

Everything else (artifact contract, four gates, scorecard, registry) is shared.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path


RUNTIME_CHOICES = ("claude", "codex")
DEFAULT_RUNTIME = "claude"


def normalize_runtime(value):
    if not value:
        return DEFAULT_RUNTIME
    lowered = str(value).strip().lower()
    if lowered not in RUNTIME_CHOICES:
        raise SystemExit(
            "Unknown runtime: {!r}. Expected one of: {}".format(
                value, ", ".join(RUNTIME_CHOICES)
            )
        )
    return lowered


# ---------------------------------------------------------------------------
# Claude Code CLI runtime (`claude -p --bare --output-format json`)
# ---------------------------------------------------------------------------

CLAUDE_DEFAULT_ALLOWED_TOOLS = "Read,Grep,Glob"
CLAUDE_DEFAULT_DISALLOWED_TOOLS = "WebFetch,WebSearch"
CLAUDE_DEFAULT_MAX_BUDGET_USD = 5.0
CLAUDE_DEFAULT_PERMISSION_MODE = "bypassPermissions"


def resolve_claude_executable():
    candidates = []
    if os.name == "nt":
        candidates.extend(["claude.cmd", "claude.exe", "claude"])
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.extend(
                [
                    str(Path(appdata) / "npm" / "claude.cmd"),
                    str(Path(appdata) / "npm" / "claude"),
                ]
            )
    else:
        candidates.append("claude")
    for candidate in candidates:
        resolved = shutil.which(candidate) if Path(candidate).name == candidate else candidate
        if resolved and Path(resolved).exists():
            return resolved
    raise FileNotFoundError("Unable to locate `claude` executable on PATH.")


def parse_claude_version(stdout):
    match = re.search(r"(\d+\.\d+\.\d+)\s*\(Claude Code\)", stdout)
    if match:
        return match.group(1)
    return stdout.splitlines()[0].strip() if stdout else "unknown"


def contains_flag(help_text, *patterns):
    for pattern in patterns:
        if re.search(r"(^|\s)" + re.escape(pattern) + r"(\s|<|$)", help_text, flags=re.MULTILINE):
            return True
    return False


def build_claude_command(args, prompt_text):
    claude_executable = getattr(args, "claude_executable", None) or resolve_claude_executable()
    add_dirs = list(getattr(args, "add_dir", []) or [])
    workspace_root = getattr(args, "workspace_root", None)
    if workspace_root and str(workspace_root) not in add_dirs:
        add_dirs.insert(0, str(workspace_root))

    command = [claude_executable, "-p"]
    if not getattr(args, "no_bare", False):
        command.append("--bare")
    command.extend(["--output-format", args.output_format])
    if getattr(args, "no_session_persistence", True):
        command.append("--no-session-persistence")
    if getattr(args, "max_budget_usd", None) is not None:
        command.extend(["--max-budget-usd", str(args.max_budget_usd)])
    if getattr(args, "effort", ""):
        command.extend(["--effort", args.effort])
    if getattr(args, "model", ""):
        command.extend(["--model", args.model])
    if getattr(args, "allowed_tools", ""):
        command.extend(["--allowedTools", args.allowed_tools])
    if getattr(args, "disallowed_tools", ""):
        command.extend(["--disallowedTools", args.disallowed_tools])
    if getattr(args, "permission_mode", ""):
        command.extend(["--permission-mode", args.permission_mode])
    for directory in add_dirs:
        command.extend(["--add-dir", directory])
    if getattr(args, "session_id", ""):
        command.extend(["--session-id", args.session_id])
    if getattr(args, "system_prompt_file", ""):
        command.extend(["--system-prompt-file", str(args.system_prompt_file)])
    if getattr(args, "append_system_prompt_file", ""):
        command.extend(
            ["--append-system-prompt-file", str(args.append_system_prompt_file)]
        )
    if getattr(args, "settings", ""):
        command.extend(["--settings", str(args.settings)])
    command.append("-")
    return command


def parse_claude_json_result(stdout):
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {"raw": stdout}
    if not isinstance(payload, dict):
        return {"raw": stdout}
    if isinstance(payload.get("result"), str):
        return payload
    content = payload.get("content")
    if isinstance(content, list):
        text_blocks = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") in {"text", None}
        ]
        if text_blocks:
            return {
                "result": "\n".join(text_blocks),
                "session_id": payload.get("session_id", ""),
                "raw": payload,
            }
    return {"raw": payload}


# ---------------------------------------------------------------------------
# Codex CLI runtime (`codex exec --output-last-message ... --json`)
# ---------------------------------------------------------------------------

CODEX_DEFAULT_REASONING_EFFORT = "xhigh"
CODEX_DEFAULT_SANDBOX = "workspace-write"
CODEX_DEFAULT_MODEL = ""
CODEX_DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT = 500000


def resolve_codex_executable():
    candidates = []
    if os.name == "nt":
        candidates.extend(["codex.cmd", "codex.exe", "codex"])
    else:
        candidates.append("codex")
    for candidate in candidates:
        resolved = shutil.which(candidate) if Path(candidate).name == candidate else candidate
        if resolved and Path(resolved).exists():
            return resolved
    raise FileNotFoundError("Unable to locate `codex` executable on PATH.")


def parse_codex_version(stdout):
    match = re.search(r"(\d+\.\d+\.\d+)", stdout)
    return match.group(1) if match else (stdout.splitlines()[0].strip() if stdout else "unknown")


def build_codex_command(args, prompt_text):
    codex_executable = getattr(args, "codex_executable", None) or resolve_codex_executable()
    reasoning_effort = getattr(args, "reasoning_effort", "") or CODEX_DEFAULT_REASONING_EFFORT
    sandbox = getattr(args, "sandbox", "") or CODEX_DEFAULT_SANDBOX
    token_limit = getattr(args, "tool_output_token_limit", None)
    model = getattr(args, "model", "")

    command = [codex_executable, "exec"]
    command.extend(["-c", "model_reasoning_effort=" + str(reasoning_effort)])
    if model:
        command.extend(["-m", model])
    if token_limit:
        command.extend(["-c", "tool_output_token_limit=" + str(token_limit)])
    command.extend(["-s", sandbox])
    workspace_root = getattr(args, "workspace_root", None)
    if workspace_root:
        command.extend(["-C", str(workspace_root)])
    for directory in list(getattr(args, "add_dir", []) or []):
        command.extend(["--add-dir", str(directory)])
    if getattr(args, "skip_git_repo_check", True):
        command.append("--skip-git-repo-check")
    if getattr(args, "ephemeral", False):
        command.append("--ephemeral")
    output_file = getattr(args, "output_file", None)
    if output_file:
        command.extend(["-o", str(output_file)])
    if getattr(args, "json_events", True):
        command.append("--json")
    command.append("-")
    return command


def parse_codex_last_message(output_file):
    if output_file is None or not Path(output_file).exists():
        return {"raw": "", "result": ""}
    text = Path(output_file).read_text(encoding="utf-8", errors="replace").strip()
    return {"result": text, "raw": text}


# ---------------------------------------------------------------------------
# Runtime registry
# ---------------------------------------------------------------------------

def runtime_describe(name):
    if name == "claude":
        return {
            "name": "claude",
            "label": "Claude Code CLI",
            "invocation": "claude -p --bare --output-format json",
            "default_child_command": "claude -p --bare --output-format json --no-session-persistence --max-budget-usd 5",
            "config_artifact": ".claude/agents/*.toml + ~/.claude/settings.json",
            "auth_facts_env": "ANTHROPIC_API_KEY (or apiKeyHelper in settings.json)",
            "output_format": "json (parsed) / raw text fallback",
        }
    if name == "codex":
        return {
            "name": "codex",
            "label": "Codex CLI",
            "invocation": "codex exec -c model_reasoning_effort=xhigh --output-last-message FILE --json",
            "default_child_command": "codex exec -c model_reasoning_effort=xhigh -s workspace-write -C WS --output-last-message OUT --json -",
            "config_artifact": "codex config.toml + project rules",
            "auth_facts_env": "Codex CLI uses configured provider auth",
            "output_format": "JSONL events on stdout + last message written to file",
        }
    raise SystemExit("Unknown runtime: {!r}".format(name))



# Transient Claude CLI failure detection
# ---------------------------------------------------------------------------
# `claude -p --output-format json` envelopes transient auth / rate-limit
# failures with `is_error: true` and a `result` string like
# `"Not logged in · Please run /login"`. The exit code stays 0, so naive
# subprocess handling writes the error string as if it were a successful
# review. These helpers let the runner distinguish those from real output
# and retry / fall back.

_CLAUDE_TRANSIENT_RESULT_PATTERNS: tuple[str, ...] = (
    r"Not logged in",
    r"Please run /login",
    r"rate.{0,5}limit",
    r"Rate limit",
    r"service unavailable",
    r"Service Unavailable",
    r"internal server error",
    r"Internal server error",
    r"please try again",
    r"Please try again",
    r"session expired",
    r"Session expired",
    r"connection reset",
    r"Connection reset",
    r"overloaded",
    r"Overloaded",
)
_CLAUDE_TRANSIENT_RESULT_RE = re.compile(
    "|".join(_CLAUDE_TRANSIENT_RESULT_PATTERNS), re.IGNORECASE
)


def is_claude_transient_envelope_failure(stdout: str) -> bool:
    """True iff the JSON envelope is `is_error: true` AND result matches a
    known transient pattern (auth flap, rate limit, server overload).

    Hard parse failures / non-JSON stdout are NOT transient — surface them.
    """
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    if not payload.get("is_error"):
        return False
    result = payload.get("result")
    if not isinstance(result, str):
        return False
    return bool(_CLAUDE_TRANSIENT_RESULT_RE.search(result))


def is_claude_not_logged_in_envelope(stdout: str) -> bool:
    """True iff the envelope is a Claude "not logged in" failure.

    Used to decide whether to drop `--bare` on retry (OAuth-only auth
    fallback, per SKILL.md §runtime-modes).
    """
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict) or not payload.get("is_error"):
        return False
    result = payload.get("result")
    return isinstance(result, str) and (
        "Not logged in" in result or "/login" in result
    )



__all__ = [
    "RUNTIME_CHOICES",
    "DEFAULT_RUNTIME",
    "normalize_runtime",
    "runtime_describe",
    "resolve_claude_executable",
    "parse_claude_version",
    "contains_flag",
    "build_claude_command",
    "parse_claude_json_result",
    "resolve_codex_executable",
    "parse_codex_version",
    "build_codex_command",
    "parse_codex_last_message",
    "CLAUDE_DEFAULT_ALLOWED_TOOLS",
    "CLAUDE_DEFAULT_DISALLOWED_TOOLS",
    "CLAUDE_DEFAULT_MAX_BUDGET_USD",
    "CLAUDE_DEFAULT_PERMISSION_MODE",
    "CODEX_DEFAULT_REASONING_EFFORT",
    "CODEX_DEFAULT_SANDBOX",
    "CODEX_DEFAULT_MODEL",
    "CODEX_DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT",
    "is_claude_transient_envelope_failure",
    "is_claude_not_logged_in_envelope",
]
