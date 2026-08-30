#!/usr/bin/env python3
"""Probe local subagent runtime facts.

By default the runtime is `claude` (Claude Code CLI).  Pass `--runtime codex`
to probe Codex CLI instead.  The probe writes `manifests/runtime-probe.json`
plus (optionally) appends a note to `protocol-audit.md`.

The four gates are:

- Product Gate: executable is installed and supports the orchestration flags.
- Session Gate: live in-session native child-agent tool evidence.
- Policy Gate: the user / task / risk profile allows spawning.
- Task Gate: the candidate task has owner / input / output / acceptance.

The recommended mode recommendation only depends on the chosen runtime.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtimes import (  # noqa: E402
    DEFAULT_RUNTIME,
    RUNTIME_CHOICES,
    contains_flag,
    normalize_runtime,
    parse_claude_version,
    parse_codex_version,
    resolve_claude_executable,
    resolve_codex_executable,
    runtime_describe,
)


def run_command(executable, args):
    try:
        completed = subprocess.run(
            [executable, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except FileNotFoundError as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}


def parse_native_tools(explicit_tools):
    env_raw = os.environ.get("CLAUDE_NATIVE_AGENT_TOOLS", "")
    env_tools = [t.strip() for t in env_raw.split(",") if t.strip()]
    seen = []
    for tool in [*explicit_tools, *env_tools]:
        if tool not in seen:
            seen.append(tool)
    return {
        "observed": bool(seen),
        "tools": seen,
        "source": "cli-args" if explicit_tools else ("env" if env_tools else "none"),
    }


def classify_session_gate(native_tooling, runtime):
    tools = [str(t) for t in native_tooling.get("tools", [])]
    source = str(native_tooling.get("source", "none"))
    if runtime == "claude":
        direct_native_tools = {"Task", "spawn_agent", "send_input", "wait_agent", "resume_agent", "close_agent"}
    else:
        direct_native_tools = {"spawn_agent", "send_input", "wait_agent", "resume_agent", "close_agent"}
    observed_direct = [t for t in tools if t in direct_native_tools]

    if observed_direct and source == "cli-args":
        return {
            "pass": True,
            "confidence": "strong",
            "observed_tools": observed_direct,
            "notes": ["Live session tool evidence was recorded explicitly."],
        }
    if observed_direct:
        return {
            "pass": True,
            "confidence": "medium",
            "observed_tools": observed_direct,
            "notes": ["Native child-agent tools were observed indirectly."],
        }
    if tools:
        return {
            "pass": True,
            "confidence": "weak",
            "observed_tools": observed_direct,
            "notes": ["Some native-tool evidence was recorded, but not the core child-agent control tools."],
        }
    return {
        "pass": False,
        "confidence": "none",
        "observed_tools": observed_direct,
        "notes": ["No live native child-agent tool evidence was recorded."],
    }


def read_json_if_exists(path):
    if not path.exists() or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def detect_claude_auth_mode():
    api_key_env = bool(os.environ.get("ANTHROPIC_API_KEY"))
    candidates = [
        Path.home() / ".claude" / "settings.json",
        Path.home() / ".claude" / "settings.local.json",
    ]
    settings_have_keyhelper = False
    for path in candidates:
        data = read_json_if_exists(path)
        env_block = data.get("env", {})
        if isinstance(env_block, dict) and "ANTHROPIC_API_KEY" in env_block:
            settings_have_keyhelper = True
            break
        if "apiKeyHelper" in data:
            settings_have_keyhelper = True
            break
    return {
        "anthropic_api_key_env": api_key_env,
        "settings_have_keyhelper": settings_have_keyhelper,
        "bare_mode_auth_supported": api_key_env or settings_have_keyhelper,
        "notes": (
            ["ANTHROPIC_API_KEY is set; --bare mode will work."]
            if api_key_env
            else [
                "ANTHROPIC_API_KEY is NOT set; --bare mode requires either this env var or apiKeyHelper in settings.",
                "If only OAuth is configured, pass `--no-bare` to run claude in default mode.",
            ]
        ),
    }


def probe_claude_runtime(workspace_root):
    try:
        executable = resolve_claude_executable()
    except FileNotFoundError as exc:
        return {
            "executable": None,
            "version": "unknown",
            "version_raw": {"ok": False, "stderr": str(exc)},
            "help_raw": {"ok": False, "stderr": str(exc)},
            "print_help_raw": {"ok": False, "stderr": str(exc)},
            "bare_capable": False,
            "output_format_capable": False,
            "budget_capable": False,
            "tool_allowlist_capable": False,
            "session_id_capable": False,
            "bare_help_excerpt": "",
            "auth_mode": detect_claude_auth_mode(),
        }

    version = run_command(executable, ["--version"])
    help_result = run_command(executable, ["--help"])
    print_help = run_command(executable, ["-p", "--help"])
    help_text = "\n".join(str(r.get("stdout", "")) for r in (help_result, print_help))
    bare_capable = contains_flag(help_text, "--bare")
    output_format_capable = contains_flag(help_text, "--output-format")
    budget_capable = contains_flag(help_text, "--max-budget-usd")
    tool_allowlist_capable = contains_flag(help_text, "--allowedTools", "--allowed-tools")
    session_id_capable = contains_flag(help_text, "--session-id")
    version_label = parse_claude_version(str(version.get("stdout", "")))
    bare_help_excerpt = ""
    if help_result.get("ok"):
        match = re.search(
            r"--bare.*?(?=\n  --|\n[A-Z][^\n]*\n  --|\Z)",
            str(help_result["stdout"]),
            flags=re.DOTALL,
        )
        if match:
            bare_help_excerpt = match.group(0).strip()

    return {
        "executable": executable,
        "version": version_label,
        "version_raw": version,
        "help_raw": help_result,
        "print_help_raw": print_help,
        "bare_capable": bare_capable,
        "output_format_capable": output_format_capable,
        "budget_capable": budget_capable,
        "tool_allowlist_capable": tool_allowlist_capable,
        "session_id_capable": session_id_capable,
        "bare_help_excerpt": bare_help_excerpt,
        "auth_mode": detect_claude_auth_mode(),
    }


def probe_codex_runtime(workspace_root):
    try:
        executable = resolve_codex_executable()
    except FileNotFoundError as exc:
        return {
            "executable": None,
            "version": "unknown",
            "version_raw": {"ok": False, "stderr": str(exc)},
            "help_raw": {"ok": False, "stderr": str(exc)},
            "exec_capable": False,
            "output_last_message_capable": False,
            "json_events_capable": False,
            "sandbox_capable": False,
            "model_reasoning_effort_capable": False,
        }

    version = run_command(executable, ["--version"])
    exec_help = run_command(executable, ["exec", "--help"])
    help_text = str(exec_help.get("stdout", ""))
    version_label = parse_codex_version(str(version.get("stdout", "")))
    return {
        "executable": executable,
        "version": version_label,
        "version_raw": version,
        "help_raw": exec_help,
        "exec_capable": exec_help.get("ok", False),
        "output_last_message_capable": contains_flag(help_text, "-o", "--output-last-message"),
        "json_events_capable": contains_flag(help_text, "--json"),
        "sandbox_capable": contains_flag(help_text, "-s", "--sandbox"),
        "model_reasoning_effort_capable": contains_flag(help_text, "-c", "--config"),
    }


def build_config_guided_evidence(workspace_root):
    project_settings = workspace_root / ".claude" / "settings.json"
    home_settings = Path.home() / ".claude" / "settings.json"
    project_agents = workspace_root / ".claude" / "agents"
    home_agents = Path.home() / ".claude" / "agents"
    project_codex_cfg = workspace_root / ".codex" / "config.toml"
    home_codex_cfg = Path.home() / ".codex" / "config.toml"
    signals = []
    if project_agents.exists():
        signals.append("project_agents_dir")
    if home_agents.exists():
        signals.append("home_agents_dir")
    if project_settings.exists():
        signals.append("project_settings")
    if home_settings.exists():
        signals.append("home_settings")
    if project_codex_cfg.exists():
        signals.append("project_codex_config")
    if home_codex_cfg.exists():
        signals.append("home_codex_config")
    return {
        "available": bool(signals),
        "signals": signals,
        "notes": (
            ["Config artifacts were found that support guided subagent setup."]
            if signals
            else ["No project/home config-guided subagent evidence was found."]
        ),
    }


def assess_recommended_mode(runtime, product_gate_pass, session_gate, auth_supported, config_available):
    if runtime == "claude":
        if product_gate_pass and session_gate["pass"] and auth_supported:
            return "native-claude-task", [
                "Product Gate and Session Gate both pass; --bare auth path is available.",
                "Prefer in-session Task tool when present, otherwise spawn `claude -p --bare` via artifacts.",
            ]
        if product_gate_pass and auth_supported:
            return "artifact-orchestrated-swarm", [
                "Product Gate passes and --bare auth path is available, but Session Gate is not strong enough.",
                "Default to artifact-orchestrated-swarm with `claude -p --bare` children.",
            ]
        if product_gate_pass and config_available:
            return "config-guided-claude-subagents", [
                "Product Gate passes but --bare auth is not configured.",
                "Use config-guided Claude Code setup (settings.json + .claude/agents) instead of spawning CLI children.",
            ]
        if product_gate_pass:
            return "config-guided-claude-subagents", [
                "Product Gate passes but auth is OAuth-only and no config artifacts exist.",
                "Config-guided setup is the more honest default than spawning bare children.",
            ]
        return "single-controller", [
            "Claude Code CLI not available or too old.",
            "Stay with single-controller until the runtime is installed/updated.",
        ]

    # runtime == "codex"
    if product_gate_pass and session_gate["pass"]:
        return "native-codex-task", [
            "Product Gate and Session Gate both pass for Codex CLI.",
            "Prefer in-session spawn_agent / Task-like tool when present, otherwise `codex exec` via artifacts.",
        ]
    if product_gate_pass:
        return "artifact-orchestrated-swarm", [
            "Codex CLI is installed but Session Gate is not strong enough.",
            "Default to artifact-orchestrated-swarm with `codex exec --output-last-message ...` children.",
        ]
    if config_available:
        return "config-guided-codex-subagents", [
            "Codex CLI is not installed but project/home Codex config exists.",
            "Use config-guided setup; install Codex CLI if you actually want to spawn children.",
        ]
    return "single-controller", [
        "Codex CLI not available; stay single-controller.",
    ]


def render_audit_note(runtime, claude_data, codex_data, native_tooling, gates, config_guided, recommended_mode, auth_supported):
    lines = ["\n## Runtime Probe\n", "- Probe file: `{manifests/runtime-probe.json}`"]
    lines.append("- Runtime: `" + runtime + "`")
    if runtime == "claude" and claude_data:
        lines.extend([
            "- Claude version: `" + claude_data["version"] + "`",
            "--bare available: `" + str(claude_data["bare_capable"]) + "`",
            "--output-format available: `" + str(claude_data["output_format_capable"]) + "`",
            "--max-budget-usd available: `" + str(claude_data["budget_capable"]) + "`",
            "--allowedTools available: `" + str(claude_data["tool_allowlist_capable"]) + "`",
            "--session-id available: `" + str(claude_data["session_id_capable"]) + "`",
            "- Auth: ANTHROPIC_API_KEY env=" + str(claude_data["auth_mode"]["anthropic_api_key_env"])
            + ", settings keyhelper=" + str(claude_data["auth_mode"]["settings_have_keyhelper"])
            + ", bare_mode_supported=" + str(auth_supported),
        ])
    if runtime == "codex" and codex_data:
        lines.extend([
            "- Codex version: `" + codex_data["version"] + "`",
            "- `codex exec --help` works: `" + str(codex_data["exec_capable"]) + "`",
            "- --output-last-message available: `" + str(codex_data["output_last_message_capable"]) + "`",
            "- --json available: `" + str(codex_data["json_events_capable"]) + "`",
            "- -s / --sandbox available: `" + str(codex_data["sandbox_capable"]) + "`",
            "- -c / --config available: `" + str(codex_data["model_reasoning_effort_capable"]) + "`",
        ])
    lines.extend([
        "- Product Gate: `" + str(gates["product_gate"]["pass"]) + "`",
        "- Session Gate: `" + str(gates["session_gate"]["pass"]) + "`",
        "- Session confidence: `" + gates["session_gate"]["confidence"] + "`",
        "- Native tooling observed: `" + str(native_tooling["observed"]) + "`",
        "- Native tools: `" + (", ".join(native_tooling["tools"]) if native_tooling["tools"] else "none") + "`",
        "- Config-guided evidence: `" + str(config_guided["available"]) + "`",
        "- Config-guided signals: `" + (", ".join(config_guided["signals"]) if config_guided["signals"] else "none") + "`",
        "- Recommended mode: `" + recommended_mode + "`",
    ])
    return "\n".join(lines) + "\n"


def main():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Probe subagent runtime facts.")
    parser.add_argument("--run-root", required=True, help="Run root where audit files live.")
    parser.add_argument("--workspace-root", default=".", help="Workspace root to inspect for project config.")
    parser.add_argument(
        "--runtime",
        choices=RUNTIME_CHOICES,
        default=DEFAULT_RUNTIME,
        help="Which subagent runtime to probe. Default: claude.",
    )
    parser.add_argument(
        "--native-tool",
        action="append",
        default=[],
        help="Record a native agent tool observed in the current session, e.g. Task.",
    )
    parser.add_argument(
        "--write-protocol-audit",
        action="store_true",
        help="Append a probe note into protocol-audit.md when it exists.",
    )
    args = parser.parse_args()

    runtime = normalize_runtime(args.runtime)
    run_root = Path(args.run_root).resolve()
    workspace_root = Path(args.workspace_root).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    manifests_dir = run_root / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)

    native_tooling = parse_native_tools(list(args.native_tool))
    config_guided = build_config_guided_evidence(workspace_root)

    claude_data = probe_claude_runtime(workspace_root) if runtime == "claude" else None
    codex_data = probe_codex_runtime(workspace_root) if runtime == "codex" else None

    if runtime == "claude":
        product_pass = bool(claude_data and claude_data["bare_capable"])
        product_notes = (
            [
                "Claude Code CLI is installed and supports `--bare` mode.",
                "This is product-layer support only; it does not prove current-session native tooling.",
            ]
            if product_pass
            else ["`claude` executable not found or `--bare` flag missing."]
        )
        auth_supported = bool(claude_data and claude_data["auth_mode"]["bare_mode_auth_supported"])
    else:
        product_pass = bool(codex_data and codex_data["exec_capable"])
        product_notes = (
            [
                "Codex CLI is installed and supports `codex exec` non-interactive mode.",
            ]
            if product_pass
            else ["`codex` executable not found or `codex exec --help` failed."]
        )
        auth_supported = True  # Codex auth is provider-config driven; probe does not block on it.

    session_gate = classify_session_gate(native_tooling, runtime)
    product_gate = {"pass": product_pass, "notes": product_notes}

    recommended_mode, assessment_notes = assess_recommended_mode(
        runtime=runtime,
        product_gate_pass=product_pass,
        session_gate=session_gate,
        auth_supported=auth_supported,
        config_available=config_guided["available"],
    )

    result = {
        "probed_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_root": str(run_root),
        "workspace_root": str(workspace_root),
        "runtime": runtime,
        "runtime_describe": runtime_describe(runtime),
        "native_tooling": native_tooling,
        "commands": {},
        "claude": claude_data,
        "codex": codex_data,
        "gates": {
            "product_gate": product_gate,
            "session_gate": session_gate,
        },
        "config_guided_evidence": config_guided,
        "assessment": {
            "recommended_mode": recommended_mode,
            "notes": assessment_notes,
        },
    }

    output_path = manifests_dir / "runtime-probe.json"
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if args.write_protocol_audit:
        audit_path = run_root / "protocol-audit.md"
        if audit_path.exists():
            note = render_audit_note(
                runtime=runtime,
                claude_data=claude_data,
                codex_data=codex_data,
                native_tooling=native_tooling,
                gates={"product_gate": product_gate, "session_gate": session_gate},
                config_guided=config_guided,
                recommended_mode=recommended_mode,
                auth_supported=auth_supported,
            )
            with audit_path.open("a", encoding="utf-8") as handle:
                handle.write(note)

    print("PROBE_FILE=" + str(output_path))
    print("RUNTIME=" + runtime)
    print("RUNTIME_VERSION=" + (claude_data["version"] if claude_data else codex_data["version"]))
    print("PRODUCT_GATE=" + str(product_gate["pass"]))
    print("SESSION_GATE=" + str(session_gate["pass"]))
    print("SESSION_CONFIDENCE=" + session_gate["confidence"])
    print("NATIVE_TOOLING_OBSERVED=" + str(native_tooling["observed"]))
    print("NATIVE_TOOLS=" + ",".join(native_tooling["tools"]))
    print("CONFIG_GUIDED_EVIDENCE=" + str(config_guided["available"]))
    if runtime == "claude" and claude_data:
        print("BARE_AUTH_SUPPORTED=" + str(auth_supported))
    print("RECOMMENDED_MODE=" + recommended_mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
