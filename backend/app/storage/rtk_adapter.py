import subprocess


class RTKAdapter:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.rtk_path = "rtk"

    async def execute_command(self, cmd: str, cwd: str | None = None) -> dict:
        if not self.enabled:
            result = subprocess.run(cmd, shell=True, capture_output=True, cwd=cwd, text=True)
            return {"output": result.stdout, "compressed": False, "return_code": result.returncode}
        rtk_cmd = f"{self.rtk_path} {cmd}"
        result = subprocess.run(rtk_cmd, shell=True, capture_output=True, cwd=cwd, text=True)
        return {"output": result.stdout, "compressed": True, "return_code": result.returncode}
