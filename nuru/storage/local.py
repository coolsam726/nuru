"""nuru.storage.local — local filesystem file backend.

Stores uploaded files under a configurable root directory, using a
UUID-prefixed filename to avoid collisions and path-traversal attacks.
"""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from typing import IO, Any


class LocalFileBackend:
    """Save files to a local directory tree.

    Args:
        upload_dir: Absolute path to the root upload directory.
            The directory is created on first use if it does not exist.
    """

    def __init__(self, upload_dir: Path | str) -> None:
        self.upload_dir = Path(upload_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        file_obj: IO[bytes],
        *,
        original_filename: str,
        directory: str = "",
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Write *file_obj* to disk and return a metadata dict.

        Returns::

            {
                "server_id": str,   # relative path used as FilePond server ID
                "path":      Path,  # absolute path of the saved file
                "filename":  str,   # final filename on disk (uuid-prefixed)
                "content_type": str,
                "size": int,
            }
        """
        suffix = Path(original_filename).suffix
        safe_name = f"{uuid.uuid4().hex}{suffix}"

        dest_dir = self.upload_dir / directory if directory else self.upload_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest = dest_dir / safe_name
        data = file_obj.read()
        dest.write_bytes(data)

        # Relative path from upload_dir root — used as server_id
        server_id = str(Path(directory) / safe_name) if directory else safe_name

        ct = content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"

        return {
            "server_id": server_id,
            "path": dest,
            "filename": safe_name,
            "content_type": ct,
            "size": len(data),
        }

    def delete(self, server_id: str) -> bool:
        """Delete a file identified by its *server_id*.

        Returns ``True`` if deleted, ``False`` if not found.
        """
        target = (self.upload_dir / server_id).resolve()
        # Security: ensure the resolved path is still under upload_dir
        try:
            target.relative_to(self.upload_dir.resolve())
        except ValueError:
            return False
        if target.exists():
            target.unlink()
            return True
        return False

    def path(self, server_id: str) -> Path | None:
        """Return the absolute Path for *server_id*, or None if not found."""
        target = (self.upload_dir / server_id).resolve()
        try:
            target.relative_to(self.upload_dir.resolve())
        except ValueError:
            return None
        return target if target.exists() else None

