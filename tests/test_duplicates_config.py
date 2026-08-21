from pathlib import Path

from fileshelf.config import Config, Rule, dump_config, load_config
from fileshelf.duplicates import find_duplicates
from fileshelf.models import FileItem
from fileshelf.scanner import scan


def test_find_duplicates(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    c = tmp_path / "c.txt"
    a.write_text("same-bytes")
    b.write_text("same-bytes")
    c.write_text("other")
    items = []
    for path in (a, b, c):
        items.append(
            FileItem(
                path=path,
                size_bytes=path.stat().st_size,
                mtime=path.stat().st_mtime,
                category="Documents",
                subcategory=None,
                extension="txt",
                reason="test",
            )
        )
    groups = find_duplicates(items)
    assert len(groups) == 1
    assert len(groups[0].files) == 2
    assert len(groups[0].extras) == 1


def test_config_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        dump_config(
            Config(
                layout="type",
                skip_duplicates=True,
                skip_directories=["build"],
                rules=[Rule(match="tax", category="Documents", subcategory="Taxes", name="tax")],
            )
        ),
        encoding="utf-8",
    )
    loaded = load_config(path)
    assert loaded.layout == "type"
    assert loaded.skip_duplicates is True
    assert loaded.skip_directories == ["build"]
    assert loaded.rules[0].subcategory == "Taxes"


def test_scanner_skips_venv_and_hidden(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("k")
    hidden = tmp_path / ".secret.txt"
    hidden.write_text("h")
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "x.py").write_text("print(1)")
    result = scan(tmp_path, recursive=True, include_hidden=False)
    names = {f.path.name for f in result.files}
    assert names == {"keep.txt"}
    assert result.skipped_dirs >= 1
