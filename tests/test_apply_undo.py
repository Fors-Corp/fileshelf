from pathlib import Path

from fileshelf.apply import apply_plan, unique_path
from fileshelf.classify import classify
from fileshelf.journal import list_sessions
from fileshelf.models import FileItem, ScanResult
from fileshelf.planner import plan_from_scan
from fileshelf.undo import undo_session


def _item(path: Path) -> FileItem:
    cat, sub, reason = classify(path)
    return FileItem(
        path=path,
        size_bytes=path.stat().st_size,
        mtime=path.stat().st_mtime,
        category=cat,
        subcategory=sub,
        extension=path.suffix.lstrip("."),
        reason=reason,
    )


def test_apply_and_undo_roundtrip(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "notes.txt").write_text("hello")
    (inbox / "song.mp3").write_text("audio")
    scan = ScanResult(root=inbox, files=[_item(p) for p in inbox.iterdir() if p.is_file()])
    plan = plan_from_scan(scan, dest=inbox, layout="type")
    result = apply_plan(plan, dry_run=False, force_home=True)
    assert len(result.moved) == 2
    assert not (inbox / "notes.txt").exists()
    assert (inbox / "Documents" / "notes.txt").exists()

    sessions = list_sessions()
    assert sessions
    undone = undo_session(result.session_id, dry_run=False)
    assert len(undone.restored) == 2
    assert (inbox / "notes.txt").exists()
    assert (inbox / "song.mp3").exists()


def test_dry_run_does_not_move(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    src = inbox / "notes.txt"
    src.write_text("hello")
    scan = ScanResult(root=inbox, files=[_item(src)])
    plan = plan_from_scan(scan, dest=inbox, layout="type")
    result = apply_plan(plan, dry_run=True, force_home=True)
    assert result.moved
    assert src.exists()
    assert list_sessions() == []


def test_refuses_home_without_force() -> None:
    from fileshelf.models import MoveAction, Plan

    plan = Plan(
        root=Path.home(),
        destination_root=Path.home() / "Downloads",
        layout="type",
        actions=[
            MoveAction(
                source=Path.home() / "x.txt",
                destination=Path.home() / "Documents" / "x.txt",
                category="Documents",
                subcategory=None,
                reason="test",
                size_bytes=1,
            )
        ],
    )
    result = apply_plan(plan, dry_run=False, force_home=False)
    assert result.moved == []
    assert any("HOME" in e for e in result.errors)


def test_unique_path(tmp_path: Path) -> None:
    a = tmp_path / "file.txt"
    a.write_text("1")
    b = unique_path(a)
    assert b == tmp_path / "file-1.txt"
