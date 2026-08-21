from pathlib import Path

from fileshelf.classify import classify
from fileshelf.models import FileItem, ScanResult
from fileshelf.planner import destination_for, plan_from_scan


def _item(path: Path, *, mtime: float = 1_700_000_000) -> FileItem:
    cat, sub, reason = classify(path)
    return FileItem(
        path=path,
        size_bytes=10,
        mtime=mtime,
        category=cat,
        subcategory=sub,
        extension=path.suffix.lstrip("."),
        reason=reason,
    )


def test_smart_nests_media_by_date(tmp_path: Path) -> None:
    dest = tmp_path / "shelf"
    item = _item(tmp_path / "IMG_1.jpg")
    target = destination_for(item, dest, "smart")
    assert target.name == "IMG_1.jpg"
    assert target.parent.parent.parent.name == "Camera"
    assert target.parent.parent.parent.parent.name == "Images"


def test_type_layout_is_flat_category(tmp_path: Path) -> None:
    dest = tmp_path / "shelf"
    item = _item(tmp_path / "notes.txt")
    target = destination_for(item, dest, "type")
    assert target == dest / "Documents" / "notes.txt"


def test_skips_already_shelved(tmp_path: Path) -> None:
    dest = tmp_path / "Documents"
    dest.mkdir()
    src = dest / "notes.txt"
    src.write_text("hi")
    scan = ScanResult(root=tmp_path, files=[_item(src)])
    plan = plan_from_scan(scan, dest=tmp_path, layout="type")
    assert plan.actions == []
    assert plan.skipped
