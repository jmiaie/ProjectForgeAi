import hashlib


def make_node_id(project_id: str, *parts: str) -> str:
    raw = "::".join([project_id, *parts])
    return hashlib.sha256(raw.encode()).hexdigest()
