"""nuru.forms.image_entry — read-only image display field for detail/form views.

Usage::

    from nuru.forms import ImageEntry

    detail_fields = [
        ImageEntry("avatar")
            .label("Profile Photo")
            .avatar()                        # circular, 24×24
            .url_prefix("/admin/uploads"),

        ImageEntry("banner")
            .label("Banner")
            .img_class("w-full h-48 object-cover rounded-lg")
            .url_prefix("/admin/uploads"),
    ]
"""

from __future__ import annotations

from .base import Field


class ImageEntry(Field):
    """Read-only image display field.

    Renders a stored file server-ID (or any URL) as an ``<img>`` tag inside
    the detail / form view.  It is *display-only* — no file-picker is shown.

    Args:
        key: Model attribute name that holds the image URL or server-ID.

    Fluent API:
        .url_prefix(prefix)          URL prefix prepended to relative server-IDs.
        .img_class(classes)          Full Tailwind class string for the <img>.
        .avatar()                    Shortcut: circular 24×24 thumbnail.
        .placeholder_icon(path_d)   SVG path data for the empty-state icon.
    """

    _FIELD_TYPE = "image"
    _INPUT_TYPE = "text"   # irrelevant — never rendered as an input

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._url_prefix: str = ""
        self._img_class: str = "w-32 h-32 object-cover rounded-lg"
        self._placeholder_icon: str = (
            "M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14"
            "m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
        )

    # ------------------------------------------------------------------ #
    # Getters                                                              #
    # ------------------------------------------------------------------ #

    def get_url_prefix(self) -> str:
        return self._url_prefix

    def get_img_class(self) -> str:
        return self._img_class

    def get_placeholder_icon(self) -> str:
        return self._placeholder_icon

    def get_url(self, value) -> str | None:
        """Build the full URL from *value*, or return None when empty."""
        if not value or str(value).strip() == "":
            return None
        v = str(value).strip()
        if v.startswith(("http://", "https://", "/")):
            return v
        prefix = self._url_prefix.rstrip("/")
        return f"{prefix}/{v}" if prefix else f"/{v}"

    # ------------------------------------------------------------------ #
    # Fluent setters                                                       #
    # ------------------------------------------------------------------ #

    def url_prefix(self, prefix: str) -> "ImageEntry":
        """Set the URL prefix prepended to relative server-IDs."""
        self._url_prefix = prefix
        return self

    def img_class(self, classes: str) -> "ImageEntry":
        """Override the Tailwind classes applied to the ``<img>`` element."""
        self._img_class = classes
        return self

    def avatar(self) -> "ImageEntry":
        """Shortcut for a circular avatar thumbnail (w-24 h-24 rounded-full)."""
        self._img_class = "w-24 h-24 rounded-full object-cover"
        self._placeholder_icon = (
            "M16 7a4 4 0 11-8 0 4 4 0 018 0z"
            "M12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
        )
        return self

    def placeholder_icon(self, path_d: str) -> "ImageEntry":
        """Set the SVG ``d`` attribute used in the empty-state placeholder."""
        self._placeholder_icon = path_d
        return self

