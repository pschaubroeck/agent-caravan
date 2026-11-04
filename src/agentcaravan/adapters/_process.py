"""Small subprocess helpers shared by runtime adapter surfaces."""

from __future__ import annotations

import os
import signal
import subprocess
from typing import Any, Callable


def run_with_process_group_timeout(
    runner: Callable[..., subprocess.CompletedProcess[str]],
    argv: list[str],
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Run with the injected seam, killing the full POSIX process group on timeout."""
    if runner is not subprocess.run or os.name != "posix":
        return runner(argv, **kwargs)

    options = dict(kwargs)
    timeout = options.pop("timeout", None)
    check = options.pop("check", False)
    capture_output = options.pop("capture_output", False)
    input_data = options.pop("input", None)
    if capture_output:
        options["stdout"] = subprocess.PIPE
        options["stderr"] = subprocess.PIPE
    if input_data is not None:
        options["stdin"] = subprocess.PIPE
    options["start_new_session"] = True

    process = subprocess.Popen(argv, **options)
    try:
        stdout, stderr = process.communicate(input=input_data, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            process.kill()
        stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(
            argv, timeout, output=stdout, stderr=stderr
        ) from error

    completed = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
    if check and completed.returncode:
        raise subprocess.CalledProcessError(
            completed.returncode, argv, output=stdout, stderr=stderr
        )
    return completed


__all__ = ["run_with_process_group_timeout"]
