"""Photo uploads. Every image is re-encoded: this strips hidden data such as GPS
location and camera details, limits size, and blocks files that aren't real images."""

import io
import secrets
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings
from app.core.errors import AppError

MAX_BYTES = 12 * 1024 * 1024
MAX_EDGE = 2000
ALLOWED = {"JPEG", "PNG", "WEBP"}
Image.MAX_IMAGE_PIXELS = 50_000_000  # refuse "decompression bomb" images


def storage_dir() -> Path:
    d = Path(get_settings().storage_local_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d


def process_upload(raw: bytes) -> tuple[str, int, int, bytes]:
    if len(raw) > MAX_BYTES:
        raise AppError("photo_too_large", 413, max_mb=MAX_BYTES // (1024 * 1024))
    try:
        img = Image.open(io.BytesIO(raw))
        if img.format not in ALLOWED:
            raise AppError("photo_bad_type", 415)
        img.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise AppError("photo_bad_type", 415) from exc
    img = ImageOps.exif_transpose(img)  # keep it upright, then drop all metadata
    img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    clean = Image.new("RGB", img.size)
    clean.paste(img)
    key = f"{secrets.token_hex(16)}.webp"
    out = io.BytesIO()
    clean.save(out, "WEBP", quality=82, method=4)
    return key, clean.width, clean.height, out.getvalue()


def store(db, photo, data: bytes) -> None:
    """Save the processed image with the configured storage backend."""
    from app.modules.community.models import PhotoBlob

    if get_settings().storage_backend == "database":
        db.add(PhotoBlob(photo_id=photo.id, data=data))
    else:
        (storage_dir() / photo.storage_key).write_bytes(data)


def load(db, photo) -> bytes | None:
    from app.modules.community.models import PhotoBlob

    blob = db.get(PhotoBlob, photo.id)
    if blob is not None:
        return blob.data
    path = storage_dir() / photo.storage_key
    return path.read_bytes() if path.is_file() else None
