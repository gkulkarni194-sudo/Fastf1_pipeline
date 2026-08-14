from __future__ import annotations

from f1_pipeline.core.hashing import file_sha256


def test_file_sha256(tmp_path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("layer0\n", encoding="utf-8")

    assert file_sha256(file_path) == "74f0f870a9d9d94d7d3d59ddd2aa5aac5b4ff5e3a8d8bd1554a1c0267bf8d8c5"
