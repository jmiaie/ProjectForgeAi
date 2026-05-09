import subprocess


class RTKAdapter:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.rtk_path = "rtk"

    async def execute_command(self, cmd: str, cwd: str | None = None):
        if self.enabled:
            cmd = f"{self.rtk_path} {cmd}"
        result = subprocess.run(cmd, shell=True, capture_output=True, cwd=cwd, check=False)
        return {
            "output": result.stdout.decode(),
            "error": result.stderr.decode(),
            "returncode": result.returncode,
            "compressed": self.enabled,
        }
