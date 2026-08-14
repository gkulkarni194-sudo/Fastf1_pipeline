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
