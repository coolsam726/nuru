"""
Heroicons icon library integration for nuru.

Icons are resolved using the official ``heroicons`` Python package
(https://pypi.org/project/heroicons/), which bundles the full Heroicons set
from the upstream source zip.  No SVG paths are hand-copied here.

Usage in Python:
    from nuru.icons import render_icon
    markup = render_icon("briefcase", "w-5 h-5")

Usage in Jinja2 templates (render_icon is registered as a global automatically):
    {{ render_icon("home", "w-4 h-4") }}
    {{ render_icon("M5 13l4 4L19 7", "w-4 h-4") }}  {# raw path still works #}

Supported styles: "outline" (default), "solid", "mini", "micro".
Raises ``heroicons.IconDoesNotExist`` for unknown named icons.
"""

from __future__ import annotations

from markupsafe import Markup, escape

from heroicons.jinja import heroicon_outline, heroicon_solid, heroicon_mini, heroicon_micro
from heroicons import IconDoesNotExist

_STYLE_FNS = {
    "outline": heroicon_outline,
    "solid":   heroicon_solid,
    "mini":    heroicon_mini,
    "micro":   heroicon_micro,
}


def _is_svg_path(value: str) -> bool:
    """Return True when *value* is a raw SVG path string rather than an icon name."""
    return value.startswith("M") or value.startswith("m") or " " in value


def _svg_wrap(path_d: str, css_class: str) -> Markup:
    """Wrap a raw SVG path-data string in a complete stroke SVG element.

    Used for backward-compatible rendering of Action(icon="M5 13...") style paths.
    """
    safe_d = escape(path_d)
    safe_cls = escape(css_class)
    return Markup(
        f'<svg class="{safe_cls}" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
        f'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="{safe_d}"/>'
        f'</svg>'
    )


def render_icon(icon: str, css_class: str = "w-4 h-4", *, style: str = "outline") -> Markup:
    """Render an icon as a safe inline SVG element.

    Args:
        icon:      A Heroicon name (e.g. ``"briefcase"``, ``"chart-bar"``) **or** a raw
                   SVG path-data string (e.g. ``"M5 13l4 4L19 7"``).  Raw paths are
                   rendered using a backward-compatible SVG wrapper and are never looked
                   up in the Heroicons library.
        css_class: CSS class(es) applied to the ``<svg>`` element.
        style:     Heroicons style — one of ``"outline"``, ``"solid"``, ``"mini"``,
                   ``"micro"``.  Ignored for raw SVG path inputs.

    Returns:
        A :class:`markupsafe.Markup` (HTML-safe) string.  Returns ``Markup("")`` when
        *icon* is empty.

    Raises:
        heroicons.IconDoesNotExist: When *icon* is a name not found in the chosen style.
    """
    if not icon:
        return Markup("")

    # Backward compat: raw SVG path-data strings (e.g. from Action(icon="M5 13..."))
    if _is_svg_path(icon):
        return _svg_wrap(icon, css_class)

    render_fn = _STYLE_FNS.get(style, heroicon_outline)
    return render_fn(icon, **{"class": css_class}, stroke_width=2)


# ---------------------------------------------------------------------------
# Shim: previous public API kept for any code that imported resolve_icon
# ---------------------------------------------------------------------------

def resolve_icon(icon_name: str) -> str:
    """Deprecated shim — use ``render_icon()`` in templates instead.

    Returns the raw SVG path-data string for the given Heroicon name, or the
    name itself if it is already a path string.  This no longer uses a
    hand-maintained dictionary; the ``heroicons`` package is queried directly.
    """
    if not icon_name:
        return ""
    if _is_svg_path(icon_name):
        return icon_name
    # Extract raw path data from the official package for callers that still
    # expect a path string rather than a full SVG element.
    import xml.etree.ElementTree as ET
    svg_markup = str(heroicon_outline(icon_name))
    root = ET.fromstring(svg_markup)
    paths = [n.attrib.get("d", "") for n in root.iter() if n.tag.endswith("path")]
    return " ".join(p for p in paths if p) or icon_name
