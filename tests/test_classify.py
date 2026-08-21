from pathlib import Path

from fileshelf.classify import classify
from fileshelf.config import Rule


def test_extension_images() -> None:
    assert classify(Path("holiday.jpg"))[0] == "Images"


def test_screenshot_heuristic() -> None:
    cat, sub, reason = classify(Path("Screenshot 2026-08-01 at 12.00.00.png"))
    assert cat == "Images"
    assert sub == "Screenshots"
    assert "screenshot" in reason


def test_camera_and_receipt() -> None:
    assert classify(Path("IMG_4021.HEIC"))[1] == "Camera"
    assert classify(Path("invoice-acme.pdf"))[1] == "Receipts"


def test_whatsapp_video() -> None:
    cat, sub, _ = classify(Path("WhatsApp Video 2026-01-01.mp4"))
    assert cat == "Videos"
    assert sub == "WhatsApp"


def test_custom_rule_overrides_builtin() -> None:
    rules = [Rule(match=r"(?i)tax", category="Documents", subcategory="Taxes", name="tax")]
    cat, sub, reason = classify(Path("tax-return.pdf"), rules=rules)
    assert cat == "Documents"
    assert sub == "Taxes"
    assert reason.startswith("rule:")


def test_unknown_is_other() -> None:
    cat, sub, _ = classify(Path("weirdfile"))
    assert cat == "Other"
    assert sub is None
