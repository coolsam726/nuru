"""nuru.forms.file_upload — FilePond-backed file upload field.

Inspired by FilamentPHP's FileUpload field.

Usage::

    from nuru.forms import FileUpload

    form_fields = [
        FileUpload("avatar")
            .label("Profile Photo")
            .image()
            .directory("avatars")
            .accept_file_types(["image/jpeg", "image/png", "image/webp"])
            .max_file_size(2 * 1024 * 1024)   # 2 MB
            .required(),

        FileUpload("documents")
            .label("Attachments")
            .multiple()
            .max_files(5)
            .accept_file_types(["application/pdf"]),
    ]
"""

from __future__ import annotations

import json
from typing import Any

from .base import Field


class FileUpload(Field):
    """A file upload field powered by FilePond.

    When ``multiple()`` is enabled the field stores a JSON-encoded list of
    server IDs (file paths) as its value.  Single-file mode stores a single
    server ID string.

    The panel must be configured with an ``upload_backend`` (or the default
    ``LocalFileBackend`` will be used automatically) and must call
    ``AdminPanel.mount()`` so the upload endpoint is registered.
    """

    _FIELD_TYPE = "file_upload"
    _INPUT_TYPE = "file"

    def __init__(self, key: str) -> None:
        super().__init__(key)

        # -- FilePond options --
        self._image_preview: bool = False          # enable image-preview plugin
        self._multiple: bool = False
        self._max_files: int | None = None
        self._accept_file_types: list[str] = []    # MIME types
        self._max_file_size: int | None = None     # bytes
        self._directory: str = ""                  # sub-directory under upload root

        # -- Filament-style toggles --
        self._can_download: bool = True
        self._can_reorder: bool = False
        self._can_preview: bool = True
        self._can_open: bool = False

        # -- image manipulation options (passed to FilePond image plugins) --
        self._image_crop_aspect_ratio: str | None = None  # e.g. "1:1"
        self._image_resize_width: int | None = None
        self._image_resize_height: int | None = None
        self._image_resize_mode: str = "cover"            # cover | contain | force

    # ------------------------------------------------------------------ #
    # Fluent setters                                                       #
    # ------------------------------------------------------------------ #

    def image(self, on: bool = True) -> "FileUpload":
        """Enable the image preview plugin — shows a thumbnail of the file."""
        self._image_preview = on
        return self

    def multiple(self, on: bool = True) -> "FileUpload":
        """Allow uploading more than one file."""
        self._multiple = on
        return self

    def max_files(self, n: int) -> "FileUpload":
        """Maximum number of files (only effective when ``multiple=True``)."""
        self._max_files = n
        return self

    def accept_file_types(self, types: list[str]) -> "FileUpload":
        """Restrict accepted MIME types, e.g. ``["image/jpeg", "image/png"]``."""
        self._accept_file_types = list(types)
        return self

    def max_file_size(self, size: int) -> "FileUpload":
        """Maximum file size **in bytes**, e.g. ``2 * 1024 * 1024`` for 2 MB."""
        self._max_file_size = size
        return self

    def directory(self, path: str) -> "FileUpload":
        """Store uploaded files in *path* sub-directory under the upload root."""
        self._directory = path.strip("/")
        return self

    def can_download(self, on: bool = True) -> "FileUpload":
        """Show a download button on uploaded files."""
        self._can_download = on
        return self

    def can_reorder(self, on: bool = True) -> "FileUpload":
        """Allow reordering files (drag-to-reorder in FilePond)."""
        self._can_reorder = on
        return self

    def can_preview(self, on: bool = True) -> "FileUpload":
        """Show a preview image for image files."""
        self._can_preview = on
        return self

    def image_crop_aspect_ratio(self, ratio: str) -> "FileUpload":
        """Lock the image crop to a specific ratio, e.g. ``"1:1"`` or ``"16:9"``."""
        self._image_crop_aspect_ratio = ratio
        return self

    def image_resize(self, *, width: int | None = None, height: int | None = None, mode: str = "cover") -> "FileUpload":
        """Resize uploaded images to *width* x *height* via FilePond's image transform plugin."""
        self._image_resize_width = width
        self._image_resize_height = height
        self._image_resize_mode = mode
        return self

    # ------------------------------------------------------------------ #
    # Getters                                                              #
    # ------------------------------------------------------------------ #

    def is_image_preview(self) -> bool:
        return self._image_preview

    def is_multiple(self) -> bool:
        return self._multiple

    def get_max_files(self) -> int | None:
        return self._max_files

    def get_accept_file_types(self) -> list[str]:
        return list(self._accept_file_types)

    def get_max_file_size(self) -> int | None:
        return self._max_file_size

    def get_directory(self) -> str:
        return self._directory

    def can_download_files(self) -> bool:
        return self._can_download

    def can_reorder_files(self) -> bool:
        return self._can_reorder

    def can_preview_files(self) -> bool:
        return self._can_preview

    def get_image_crop_aspect_ratio(self) -> str | None:
        return self._image_crop_aspect_ratio

    def get_image_resize_width(self) -> int | None:
        return self._image_resize_width

    def get_image_resize_height(self) -> int | None:
        return self._image_resize_height

    def get_image_resize_mode(self) -> str:
        return self._image_resize_mode

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def parse_value(self, raw: str | None) -> list[str]:
        """Parse a stored value (string or JSON list) into a list of server IDs."""
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        except (ValueError, TypeError):
            pass
        return [raw] if raw else []

    def serialize_value(self, server_ids: list[str]) -> str | None:
        """Serialize a list of server IDs back to the stored string.

        Single-file mode returns the bare string; multi-file returns JSON.
        """
        if not server_ids:
            return None
        if self._multiple:
            return json.dumps(server_ids)
        return server_ids[0]

    def filepond_config(self, *, upload_url: str) -> dict[str, Any]:
        """Return a dict of FilePond configuration options for the template."""
        cfg: dict[str, Any] = {
            "allowMultiple": self._multiple,
            "server": {
                "process": {
                    "url": f"{upload_url}?directory={self._directory}",
                    "method": "POST",
                    "withCredentials": False,
                },
                "revert": {
                    "url": upload_url,
                    "method": "DELETE",
                },
                "restore": f"{upload_url}/restore",
                "load": f"{upload_url}/load",
            },
        }
        if self._max_files is not None:
            cfg["maxFiles"] = self._max_files
        if self._accept_file_types:
            cfg["acceptedFileTypes"] = self._accept_file_types
        if self._max_file_size is not None:
            # FilePond expects a string like "2MB" or bytes int
            cfg["maxFileSize"] = self._max_file_size
        if self._image_crop_aspect_ratio:
            cfg["imageCropAspectRatio"] = self._image_crop_aspect_ratio
        if self._image_resize_width or self._image_resize_height:
            cfg["imageResizeTargetWidth"] = self._image_resize_width
            cfg["imageResizeTargetHeight"] = self._image_resize_height
            cfg["imageResizeMode"] = self._image_resize_mode
        if self._can_reorder:
            cfg["allowReorder"] = True
        if not self._can_preview:
            cfg["allowImagePreview"] = False
        return cfg

