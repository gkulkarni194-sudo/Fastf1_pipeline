from __future__ import annotations

from hashlib import sha256
from pathlib import Path


def file_sha256(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    file_path = Path(path)
    digest = sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)

    return digest.hexdigest()

def hash_dict(data: dict) -> str:
    """Generate a deterministic hash for a dictionary."""
    import json
    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return sha256(json_str.encode("utf-8")).hexdigest()
