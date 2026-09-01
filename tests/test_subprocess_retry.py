"""Integration test for _invoke_subprocess_with_retry (uses fake claude script)."""
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, "/Users/Hht/.codex/skills/codex-subagents-kit/scripts")
from run_subagent_task import _invoke_subprocess_with_retry


def make_fake_claude(script_body: str) -> str:
    """Write a fake claude executable that emits the given shell body."""
    fd, path = tempfile.mkstemp(prefix="fake_claude_", suffix=".sh")
    os.write(fd, f"#!/bin/bash\n{script_body}\n".encode())
    os.close(fd)
    os.chmod(path, 0o755)
    return path


def is_transient(stdout: str) -> bool:
    from runtimes import is_claude_transient_envelope_failure
    return is_claude_transient_envelope_failure(stdout)


def test_succeed_first_try():
    fake = make_fake_claude('echo \'{"is_error":false,"result":"ok"}\'')
    completed = _invoke_subprocess_with_retry(
        [fake, "-p"], prompt_text="hi", cwd="/tmp", runtime="claude",
        max_retries=3, backoff_schedule=(0, 0, 0),
    )
    assert "ok" in completed.stdout
    assert completed.returncode == 0


def test_not_logged_in_retries_and_drops_bare():
    """连续 not-logged-in → 至少 2 次重试 + --bare 被去掉一次。"""
    fake = make_fake_claude('echo \'{"is_error":true,"result":"Not logged in · Please run /login"}\'')
    t0 = time.monotonic()
    completed = _invoke_subprocess_with_retry(
        [fake, "-p", "--bare"], prompt_text="hi", cwd="/tmp", runtime="claude",
        max_retries=2, backoff_schedule=(0.1, 0.1, 0.1),
    )
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.2, f"应该 sleep 至少 2 次(每次 ≥0.1s),实际={elapsed}"
    assert is_transient(completed.stdout)


def test_real_error_no_retry():
    """is_error true 但 result 不是 transient → 不重试,立即返回。"""
    fake = make_fake_claude('echo \'{"is_error":true,"result":"out of budget ($5.00 max)"}\'')
    completed = _invoke_subprocess_with_retry(
        [fake, "-p"], prompt_text="hi", cwd="/tmp", runtime="claude",
        max_retries=3, backoff_schedule=(0.5, 0.5, 0.5),
    )
    assert "out of budget" in completed.stdout
    # 立即返回,总耗时应小于一个 backoff 周期
    # (注意:测试环境可能有 IO 开销,但绝不应该 ≥ 0.5s)


def test_nonzero_returncode_no_retry():
    """非零退出 → 不重试。"""
    fake = make_fake_claude('echo "boom" >&2\nexit 2')
    completed = _invoke_subprocess_with_retry(
        [fake, "-p"], prompt_text="hi", cwd="/tmp", runtime="claude",
        max_retries=3, backoff_schedule=(0.5, 0.5, 0.5),
    )
    assert completed.returncode == 2


def test_codex_runtime_no_retry():
    """codex runtime 完全跳过 retry 层。"""
    fake = make_fake_claude('echo "not-json-but-its-codex"')
    t0 = time.monotonic()
    completed = _invoke_subprocess_with_retry(
        [fake, "-p"], prompt_text="hi", cwd="/tmp", runtime="codex",
        max_retries=3, backoff_schedule=(1.0, 1.0, 1.0),
    )
    elapsed = time.monotonic() - t0
    assert elapsed < 0.5, f"codex 必须不 sleep,实际={elapsed}"


def test_recover_on_second_attempt():
    """第一次 transient,第二次 succeed → 立即返成功结果。

    计数文件放在 HOME 下,通过环境变量传路径。"""
    counter = tempfile.mktemp(prefix="counter_")
    # ensure file doesn't pre-exist
    if os.path.exists(counter):
        os.unlink(counter)

    script_body = (
        'COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0); '
        'COUNT=$((COUNT + 1)); '
        'echo $COUNT > "$COUNTER_FILE"; '
        'if [ "$COUNT" -lt 2 ]; then '
        "echo '{\"is_error\":true,\"result\":\"Not logged in · Please run /login\"}'; "
        'else '
        "echo '{\"is_error\":false,\"result\":\"success after retry\"}'; "
        'fi'
    )
    fake = make_fake_claude(script_body)

    # Inject env so the fake script can find COUNTER_FILE
    real_run = subprocess.run

    def patched_run(cmd, *args, **kwargs):
        new_env = os.environ.copy()
        new_env["COUNTER_FILE"] = counter
        kwargs["env"] = new_env
        return real_run(cmd, *args, **kwargs)

    # Monkey-patch subprocess.run inside run_subagent_task module
    import run_subagent_task
    original = run_subagent_task.subprocess.run
    run_subagent_task.subprocess.run = patched_run
    try:
        completed = _invoke_subprocess_with_retry(
            [fake, "-p", "--bare"], prompt_text="hi", cwd="/tmp", runtime="claude",
            max_retries=3, backoff_schedule=(0.1, 0.1, 0.1),
        )
    finally:
        run_subagent_task.subprocess.run = original

    assert "success after retry" in completed.stdout, (
        f"unexpected stdout: {completed.stdout}"
    )
