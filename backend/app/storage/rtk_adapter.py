"""RTK (context optimization) adapter.

Wraps shell command execution so we can transparently route through ``rtk``
when available and fall back to plain ``subprocess`` otherwise.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any


class RTKAdapter:
    def __init__(self, enabled: bool = True, rtk_path: str = "rtk"):
        self.enabled = enabled and shutil.which(rtk_path) is not None
        self.rtk_path = rtk_path

    async def execute_command(
        self, cmd: str, cwd: str | None = None, timeout: int | None = 60
    ) -> dict[str, Any]:
        full_cmd = f"{self.rtk_path} {cmd}" if self.enabled else cmd
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            cwd=cwd,
            timeout=timeout,
        )
        return {
            "command": full_cmd,
            "exit_code": result.returncode,
            "output": result.stdout.decode(errors="replace"),
            "stderr": result.stderr.decode(errors="replace"),
            "compressed": self.enabled,
        }
