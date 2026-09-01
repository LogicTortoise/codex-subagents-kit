"""Unit tests for retry helpers — runs without invoking claude."""
import sys
sys.path.insert(0, "/Users/Hht/.codex/skills/codex-subagents-kit/scripts")
from runtimes import (
    is_claude_transient_envelope_failure,
    is_claude_not_logged_in_envelope,
)


def test_non_envelope_returns_false():
    # Valid envelope with is_error: false
    assert not is_claude_transient_envelope_failure('{"is_error": false, "result": "ok"}')
    # Hard parse error — not transient
    assert not is_claude_transient_envelope_failure("not json at all")
    # Empty
    assert not is_claude_transient_envelope_failure("")
    # Non-dict JSON
    assert not is_claude_transient_envelope_failure('"hello"')


def test_real_success_returns_false():
    # Real result with realistic text
    assert not is_claude_transient_envelope_failure(
        '{"is_error": false, "result": "All checks passed. "}'
    )


def test_not_logged_in_returns_true():
    # The exact failure we saw
    s = '{"is_error":true,"duration_api_ms":0,"num_turns":1,"stop_reason":"stop_sequence","session_id":"3fd635a5","total_cost_usd":0,"usage":{"output_tokens_details":{"thinking_tokens":0},"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":0},"inference_geo":"","iterations":[],"speed":"standard"},"modelUsage":{},"permission_denials":[],"terminal_reason":"api_error","fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","subagent_stats":{"spawned":0,"requested":{"background":0,"foreground":0,"unset":0},"started_in_background":0,"max_depth":0,"spawned_by_subagents":0,"completed":0,"failed":0,"killed":{"parent":0,"user":0,"system":0},"refused":{"depth_limit":0,"concurrency_limit":0,"budget":0},"by_type":{}},"subtype":"success","api_error_status":null,"result":"Not logged in · Please run /login","type":"result","duration_ms":78}'
    assert is_claude_transient_envelope_failure(s)
    assert is_claude_not_logged_in_envelope(s)


def test_rate_limit_returns_true():
    s = '{"is_error":true,"result":"rate limit exceeded. please try again in 30s"}'
    assert is_claude_transient_envelope_failure(s)
    assert not is_claude_not_logged_in_envelope(s)


def test_overloaded_returns_true():
    s = '{"is_error":true,"result":"anthropic api overloaded"}'
    assert is_claude_transient_envelope_failure(s)


def test_real_error_not_transient():
    # is_error: true but result is a real failure (e.g., "out of budget")
    s = '{"is_error":true,"result":"out of budget ($5.00 max)"}'
    assert not is_claude_transient_envelope_failure(s)
    # Should not match either
    assert not is_claude_not_logged_in_envelope(s)


def test_internal_error_returns_true():
    s = '{"is_error":true,"result":"Internal server error"}'
    assert is_claude_transient_envelope_failure(s)
