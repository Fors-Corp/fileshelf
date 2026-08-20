"""Classify files by extension and filename heuristics."""

from __future__ import annotations

import re
from pathlib import Path

# Lowercase extension → (category, default subcategory or None)
_EXT: dict[str, tuple[str, str | None]] = {}


def _load(category: str, extensions: tuple[str, ...], subcategory: str | None = None) -> None:
    for ext in extensions:
        _EXT[ext.lower().lstrip(".")] = (category, subcategory)


_load(
    "Images",
    ("jpg", "jpeg", "png", "gif", "webp", "heic", "heif", "bmp", "tif", "tiff",
     "raw", "cr2", "nef", "dng", "arw", "svg", "ico", "avif", "jfif"),
)
_load(
    "Videos",
    ("mp4", "mov", "mkv", "avi", "webm", "m4v", "wmv", "flv", "mpeg", "mpg", "3gp"),
)
_load(
    "Audio",
    ("mp3", "wav", "flac", "aac", "m4a", "ogg", "wma", "aiff", "aif", "opus", "alac"),
)
_load(
    "Documents",
    ("pdf", "doc", "docx", "txt", "rtf", "odt", "pages", "md", "tex", "text"),
)
_load("Spreadsheets", ("xls", "xlsx", "csv", "ods", "numbers", "tsv"))
_load("Presentations", ("ppt", "pptx", "key", "odp"))
_load("Ebooks", ("epub", "mobi", "azw", "azw3", "fb2"))
_load(
    "Archives",
    ("zip", "tar", "gz", "tgz", "bz2", "7z", "rar", "xz", "iso", "cab"),
)
_load(
    "Installers",
    ("pkg", "dmg", "exe", "msi", "deb", "rpm", "appimage", "apk"),
)
_load(
    "Code",
    ("py", "js", "ts", "jsx", "tsx", "go", "rs", "java", "c", "cpp", "h", "hpp",
     "rb", "php", "swift", "kt", "json", "yaml", "yml", "toml", "xml", "html",
     "css", "sh", "zsh", "bash", "sql", "ipynb", "r", "lua", "vue", "svelte"),
)
_load("Fonts", ("ttf", "otf", "woff", "woff2", "eot"))
_load(
    "Design",
    ("psd", "ai", "sketch", "fig", "xd", "blend", "aep", "indd", "afdesign", "afphoto"),
)
_load("3D", ("obj", "fbx", "stl", "gltf", "glb", "3ds", "dae"))

_SCREENSHOT = re.compile(
    r"^(screenshot|screen[ _-]?shot|captura|capture|screen recording)",
    re.I,
)
_CAMERA = re.compile(
    r"^(img[_-]?\d|dsc[_-]?\d|dcim|photo[_-]?\d|pxl[_-]|vid[_-]?\d)",
    re.I,
)
_WHATSAPP = re.compile(r"whatsapp", re.I)
_RECEIPT = re.compile(
    r"(invoice|receipt|factura|recibo|bill[-_ ]?of|statement[-_ ]?\d)",
    re.I,
)


def extension_of(path: Path) -> str:
    name = path.name
    if name.startswith(".") and name.count(".") == 1:
        return ""
    return path.suffix.lower().lstrip(".")


def classify(path: Path) -> tuple[str, str | None, str]:
    """Return (category, subcategory, reason)."""
    name = path.name
    ext = extension_of(path)

    if _WHATSAPP.search(name):
        cat, _ = _EXT.get(ext, ("Images", None))
        if ext in ("mp4", "mov", "mkv", "avi", "webm", "m4v"):
            return "Videos", "WhatsApp", "whatsapp filename"
        if ext in ("mp3", "wav", "m4a", "ogg", "opus", "aac"):
            return "Audio", "WhatsApp", "whatsapp filename"
        return "Images", "WhatsApp", "whatsapp filename"

    if _SCREENSHOT.search(name):
        if ext in ("mp4", "mov", "mkv", "webm", "m4v"):
            return "Videos", "Screen Recordings", "screen recording filename"
        return "Images", "Screenshots", "screenshot filename"

    if _CAMERA.search(name):
        if ext in ("mp4", "mov", "mkv", "avi", "webm", "m4v", "3gp"):
            return "Videos", "Camera", "camera-roll filename"
        return "Images", "Camera", "camera-roll filename"

    if _RECEIPT.search(name):
        return "Documents", "Receipts", "invoice/receipt filename"

    if ext in _EXT:
        category, subcategory = _EXT[ext]
        return category, subcategory, f".{ext} file"

    return "Other", None, "unrecognized type"


def category_order() -> tuple[str, ...]:
    return (
        "Images",
        "Videos",
        "Audio",
        "Documents",
        "Spreadsheets",
        "Presentations",
        "Ebooks",
        "Archives",
        "Installers",
        "Code",
        "Fonts",
        "Design",
        "3D",
        "Other",
    )
