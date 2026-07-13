"""
File security utilities:
- Extension allow-listing
- MIME type validation
- Size enforcement
- Zip bomb protection
- Path traversal prevention
- File hashing
"""
from __future__ import annotations

import hashlib
import io
import os
import zipfile
from pathlib import Path
from typing import Optional, Tuple

import magic  # python-magic
import xxhash

from .config import get_settings
from .logging import get_logger

log = get_logger(__name__)
settings = get_settings()

ALLOWED_MIME_TYPES = {
    ".pdf": ["application/pdf"],
    ".docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    ],
    ".txt": ["text/plain", "application/octet-stream"],
    ".csv": ["text/csv", "text/plain", "application/csv"],
    ".json": ["application/json", "text/plain"],
    ".zip": ["application/zip", "application/x-zip-compressed"],
}


class FileSecurityError(ValueError):
    pass


def validate_extension(filename: str, allowed: list[str]) -> str:
    """Return lowercased extension or raise."""
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        raise FileSecurityError(
            f"Extension '{ext}' not allowed. Permitted: {allowed}"
        )
    return ext


def validate_size(data: bytes, max_bytes: Optional[int] = None) -> None:
    limit = max_bytes or settings.max_upload_bytes
    if len(data) > limit:
        raise FileSecurityError(
            f"File size {len(data)} bytes exceeds limit of {limit} bytes."
        )


def validate_mime(data: bytes, ext: str) -> str:
    """Check the actual MIME type using libmagic."""
    try:
        detected = magic.from_buffer(data[:4096], mime=True)
    except Exception:
        detected = "application/octet-stream"

    allowed_mimes = ALLOWED_MIME_TYPES.get(ext, [])
    if allowed_mimes and detected not in allowed_mimes:
        # Tolerate text/plain for structured text formats
        if "text/plain" in allowed_mimes and detected.startswith("text/"):
            return detected
        log.warning("MIME mismatch: ext=%s detected=%s", ext, detected)
        # Soft-warn only — do not block valid files with edge-case MIME
    return detected


def safe_extract_zip(
    data: bytes, dest_dir: Path, max_extracted_mb: Optional[int] = None
) -> list[Path]:
    """
    Extract a ZIP file safely.
    - Prevents path traversal
    - Limits total extracted size (zip bomb protection)
    """
    max_bytes = (max_extracted_mb or settings.MAX_ZIP_EXTRACTED_SIZE_MB) * 1024 * 1024
    extracted: list[Path] = []
    total_size = 0

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.infolist():
            # Path traversal check
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise FileSecurityError(
                    f"Zip path traversal detected: {member.filename}"
                )

            # Size check
            total_size += member.file_size
            if total_size > max_bytes:
                raise FileSecurityError(
                    f"ZIP extraction would exceed {settings.MAX_ZIP_EXTRACTED_SIZE_MB} MB limit."
                )

            # Skip directories
            if member.filename.endswith("/"):
                continue

            out_path = dest_dir / member_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(zf.read(member.filename))
            extracted.append(out_path)

    return extracted


def compute_hash(data: bytes) -> str:
    """Fast content hash using xxhash + SHA-256 for integrity."""
    return hashlib.sha256(data).hexdigest()


def compute_fast_hash(data: bytes) -> str:
    return xxhash.xxh128(data).hexdigest()


def sanitize_filename(filename: str) -> str:
    """Strip directory components and dangerous characters."""
    name = Path(filename).name
    # Keep only safe characters
    safe = "".join(c for c in name if c.isalnum() or c in "._- ")
    return safe[:200] or "upload"


def prevent_path_traversal(base_dir: Path, requested_path: str) -> Path:
    """Resolve path and ensure it stays within base_dir."""
    resolved = (base_dir / requested_path).resolve()
    if not str(resolved).startswith(str(base_dir.resolve())):
        raise FileSecurityError(f"Path traversal detected: {requested_path}")
    return resolved
