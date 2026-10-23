"""Execution of opt-in runnable code blocks.

Safety model (v1):
- A block runs only if its fence info string contains the `docsdrift:run` marker
  AND its language has a configured runtime in the allowlist.
- Shell languages (bash/sh/cmd/...) additionally require explicit opt-in via
  config `allow_shell: true` or the --allow-shell flag.
- Every run is subject to a timeout and receives a scrubbed environment that
  contains no credentials or tokens - only the minimal variables a runtime
  needs to start.
- On GitHub Actions `pull_request` events (untrusted code by definition),
  execution is refused entirely unless --trust-pr is passed.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from .config import SHELL_LANGUAGES, Config
from .markdown import CodeBlock

SAFE_ENV_KEYS = (
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
    "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "LC_ALL",
)


@dataclass
class RunResult:
    path: str
    line: int
    language: str
    status: str  # "pass" | "fail" | "timeout" | "skipped"
    detail: str = ""


def safe_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k in SAFE_ENV_KEYS}


def pr_execution_blocked(environ: dict | None = None, trust_pr: bool = False) -> bool:
    env = os.environ if environ is None else environ
    return env.get("GITHUB_EVENT_NAME") == "pull_request" and not trust_pr


def run_block(
    block: CodeBlock,
    path: str,
    config: Config,
    allow_shell: bool = False,
    timeout: float | None = None,
) -> RunResult:
    cmd = config.runtime_for(block.language)
    if cmd is None:
        return RunResult(path, block.line, block.language, "skipped",
                         f"no runtime configured for language '{block.language}'")
    if block.language in SHELL_LANGUAGES and not (allow_shell or config.allow_shell):
        return RunResult(path, block.line, block.language, "skipped",
                         "shell execution requires explicit opt-in (allow_shell / --allow-shell)")

    limit = timeout if timeout is not None else config.timeout_seconds
    # If the runtime command contains a {code} placeholder the snippet is passed
    # as an argument (e.g. ["python", "-c", "{code}"]); otherwise it is fed to
    # the runtime on stdin (e.g. ["bash"]).
    if any("{code}" in part for part in cmd):
        argv = [part.replace("{code}", block.code) for part in cmd]
        stdin = None
    else:
        argv = cmd
        stdin = block.code
    try:
        proc = subprocess.run(
            argv,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=limit,
            env=safe_env(),
        )
    except FileNotFoundError:
        return RunResult(path, block.line, block.language, "fail",
                         f"runtime not found on PATH: {cmd[0]}")
    except subprocess.TimeoutExpired:
        return RunResult(path, block.line, block.language, "timeout",
                         f"exceeded timeout of {limit:g}s")
    except OSError as e:
        return RunResult(path, block.line, block.language, "fail", f"failed to start runtime: {e}")

    if proc.returncode == 0:
        return RunResult(path, block.line, block.language, "pass")
    output = (proc.stderr or proc.stdout or "").strip()
    return RunResult(path, block.line, block.language, "fail",
                     f"exit code {proc.returncode}\n{output}" if output
                     else f"exit code {proc.returncode}")
