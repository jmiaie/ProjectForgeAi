import os


class OmpaAdapter:
    def __init__(self, project_id: str):
        self.vault_path = f"./vaults/project_{project_id}"
        os.makedirs(self.vault_path, exist_ok=True)
        self._fallback_log: list[str] = []

        try:
            from ompa import Ompa  # type: ignore
        except ImportError:
            self.ao = None
        else:
            self.ao = Ompa(vault_path=self.vault_path)

    async def record_decision(self, message: str) -> None:
        if self.ao is None:
            self._fallback_log.append(message)
            return
        self.ao.classify(message)

    async def session_start(self):
        if self.ao is None:
            return {"status": "started", "mode": "fallback"}
        return self.ao.session_start()
