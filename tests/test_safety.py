from pathlib import Path

from fileshelf.safety import deny_reason, is_denied, is_home


def test_system_paths_denied() -> None:
    assert is_denied(Path("/usr"))
    assert is_denied(Path("/System"))
    assert is_denied(Path("/"))
    assert deny_reason(Path("/Applications")) == "protected system path"


def test_downloads_allowed() -> None:
    downloads = Path.home() / "Downloads"
    assert not is_denied(downloads)


def test_home_detection() -> None:
    assert is_home(Path.home())
    assert not is_home(Path.home() / "Downloads")
