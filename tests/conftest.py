from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data = tmp_path / "fileshelf-data"
    data.mkdir()
    monkeypatch.setattr("fileshelf.journal.data_dir", lambda: data)
    monkeypatch.setattr("fileshelf.config.data_dir", lambda: data)
    return data
