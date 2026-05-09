import os


class InMemoryOmpa:
    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.records: list[str] = []

    def classify(self, message: str) -> None:
        self.records.append(message)

    def session_start(self) -> dict:
        return {"vault_path": self.vault_path, "status": "started"}


class OmpaAdapter:
    def __init__(self, project_id: str):
        self.vault_path = f"./vaults/project_{project_id}"
        os.makedirs(self.vault_path, exist_ok=True)
        try:
            from ompa import Ompa
        except ImportError:
            Ompa = InMemoryOmpa
        self.ao = Ompa(vault_path=self.vault_path)

    async def record_decision(self, message: str) -> None:
        self.ao.classify(message)

    async def session_start(self):
        return self.ao.session_start()
