"""
Color palette generator for nuru admin panels.

Accepts any CSS color value (hex, rgb/rgba, oklch, hsl, named) and generates
a Tailwind 4-compatible 50–950 scale as CSS custom properties.

The generation strategy:
  1. Parse the input to linear-light sRGB.
  2. Convert to OKLch (perceptually uniform, same space Tailwind 4 uses).
  3. Interpolate lightness across the 50–950 stops while keeping hue and
     chroma proportional to the input — vivid colours stay vivid, muted
     colours stay muted.
  4. Emit CSS ``--color-{name}-{stop}`` variables in oklch() syntax.

No third-party libraries are required — stdlib only.
"""

from __future__ import annotations

import math
import re
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Stop definitions: (stop_number, target_lightness_in_oklch)
# Lightness range is 0-1.  These mirror Tailwind's own palette structure.
# ---------------------------------------------------------------------------
_STOPS: list[tuple[int, float]] = [
    (50,  0.971),
    (100, 0.936),
    (200, 0.870),
    (300, 0.790),
    (400, 0.698),
    (500, 0.588),   # ← "500" is the canonical base (closest to input)
    (600, 0.493),
    (700, 0.406),
    (800, 0.332),
    (900, 0.267),
    (950, 0.236),
]


class OKLch(NamedTuple):
    L: float  # 0–1
    C: float  # 0–≈0.4
    H: float  # 0–360 degrees


# ---------------------------------------------------------------------------
# Colour parsing
# ---------------------------------------------------------------------------

def _linearize(c: float) -> float:
    """sRGB component → linear light."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _delinearize(c: float) -> float:
    """Linear light → sRGB component."""
    c = max(0.0, min(1.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def _rgb01_to_oklch(r: float, g: float, b: float) -> OKLch:
    rl, gl, bl = _linearize(r), _linearize(g), _linearize(b)
    # Linear sRGB → OKLab (Björn Ottosson's transform)
    X = 0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl
    Y = 0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl
    Z = 0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl
    l_ = X ** (1 / 3)
    m_ = Y ** (1 / 3)
    s_ = Z ** (1 / 3)
    L  =  0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a  =  1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb =  0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C  = math.sqrt(a * a + bb * bb)
    H  = math.degrees(math.atan2(bb, a)) % 360
    return OKLch(L, C, H)


def _oklch_to_rgb01(lch: OKLch) -> tuple[float, float, float]:
    L, C, H = lch
    h_rad = math.radians(H)
    a = C * math.cos(h_rad)
    bb = C * math.sin(h_rad)
    l_ = L + 0.3963377774 * a + 0.2158037573 * bb
    m_ = L - 0.1055613458 * a - 0.0638541728 * bb
    s_ = L - 0.0894841775 * a - 1.2914855480 * bb
    l3, m3, s3 = l_ ** 3, m_ ** 3, s_ ** 3
    X =  4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3
    Y = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3
    Z = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3
    r = _delinearize( 4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3)
    g = _delinearize(-1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3)
    b = _delinearize(-0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3)
    return r, g, b


def _parse_hex(value: str) -> tuple[float, float, float] | None:
    h = value.strip().lstrip('#')
    if re.fullmatch(r'[0-9a-fA-F]{3}', h):
        h = ''.join(c * 2 for c in h)
    if re.fullmatch(r'[0-9a-fA-F]{6}', h):
        return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    if re.fullmatch(r'[0-9a-fA-F]{8}', h):  # with alpha — ignore alpha
        return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return None


_CSS_NAMED: dict[str, str] = {
    # Minimal set; full named colour list omitted for brevity — hex fallback covers real use.
    "black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000",
    "blue": "#0000ff", "yellow": "#ffff00", "orange": "#ffa500", "purple": "#800080",
    "pink": "#ffc0cb", "indigo": "#4b0082", "teal": "#008080", "cyan": "#00ffff",
}


def _parse_rgb(value: str) -> tuple[float, float, float] | None:
    """Parse rgb(r g b) or rgb(r, g, b) — percent or 0-255 integers."""
    m = re.match(r'rgba?\(\s*([^)]+)\)', value.strip(), re.I)
    if not m:
        return None
    parts = re.split(r'[,\s/]+', m.group(1).strip())
    parts = [p for p in parts if p]
    if len(parts) < 3:
        return None

    def parse_component(s: str) -> float:
        s = s.strip()
        if s.endswith('%'):
            return float(s[:-1]) / 100
        v = float(s)
        return v / 255 if v > 1 else v

    return parse_component(parts[0]), parse_component(parts[1]), parse_component(parts[2])


def _parse_hsl(value: str) -> tuple[float, float, float] | None:
    m = re.match(r'hsla?\(\s*([^)]+)\)', value.strip(), re.I)
    if not m:
        return None
    parts = re.split(r'[,\s/]+', m.group(1).strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) < 3:
        return None
    h = float(parts[0].rstrip('deg')) / 360
    s = float(parts[1].rstrip('%')) / 100
    l = float(parts[2].rstrip('%')) / 100
    import colorsys
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return r, g, b


def _parse_oklch(value: str) -> OKLch | None:
    """Parse oklch(L C H) where L can be 0-1 or 0%-100%, C is 0-≈0.4, H is degrees."""
    m = re.match(r'oklch\(\s*([^)]+)\)', value.strip(), re.I)
    if not m:
        return None
    parts = re.split(r'[,\s/]+', m.group(1).strip())
    parts = [p.strip() for p in parts if p.strip() and p.strip() != 'none']
    if len(parts) < 3:
        return None
    L_raw = parts[0]
    L = float(L_raw.rstrip('%')) / (100 if L_raw.endswith('%') else 1)
    C = float(parts[1])
    H = float(parts[2].rstrip('deg')) % 360
    return OKLch(L, C, H)


def parse_color(value: str) -> OKLch:
    """Parse any supported CSS colour string to OKLch.

    Supported formats: hex (#rgb, #rrggbb, #rrggbbaa), rgb/rgba(),
    hsl/hsla(), oklch(), and a small set of CSS named colours.

    Raises ValueError for unrecognised formats.
    """
    v = value.strip()

    # oklch — most direct
    lch = _parse_oklch(v)
    if lch:
        return lch

    # named colour → recurse via hex
    if v.lower() in _CSS_NAMED:
        return parse_color(_CSS_NAMED[v.lower()])

    # hex
    rgb = _parse_hex(v)
    if rgb:
        return _rgb01_to_oklch(*rgb)

    # rgb/rgba
    rgb = _parse_rgb(v)
    if rgb:
        return _rgb01_to_oklch(*rgb)

    # hsl/hsla
    rgb = _parse_hsl(v)
    if rgb:
        return _rgb01_to_oklch(*rgb)

    raise ValueError(
        f"Cannot parse colour {value!r}. "
        "Supported formats: hex, rgb(), rgba(), hsl(), hsla(), oklch()."
    )


# ---------------------------------------------------------------------------
# Palette generation
# ---------------------------------------------------------------------------

def _scale_chroma(C_base: float, L_base: float, L_target: float) -> float:
    """
    Reduce chroma towards the extremes of the lightness scale so that very
    light and very dark stops don't produce out-of-gamut colours.

    The scaling mirrors the pattern in Tailwind's own generated palettes:
    chroma drops off smoothly as lightness moves away from the 500-level base.
    """
    distance = abs(L_target - L_base)
    # Linear reduction: at full distance (0.7 ≈ white to base) chroma → 0
    factor = max(0.0, 1.0 - distance / 0.70)
    return C_base * factor


def generate_palette(color: str) -> dict[int, str]:
    """Generate a {stop: oklch_string} palette from any CSS colour.

    Returns a dict mapping stop numbers (50, 100, …, 950) to CSS oklch()
    strings ready to embed in a stylesheet.
    """
    base = parse_color(color)
    result: dict[int, str] = {}
    for stop, L_target in _STOPS:
        C_target = _scale_chroma(base.C, base.L, L_target)
        # Round to 4 significant figures to keep CSS concise
        result[stop] = f"oklch({L_target:.4f} {C_target:.4f} {base.H:.2f})"
    return result


def palette_css_vars(name: str, color: str) -> str:
    """Return a block of CSS custom property declarations for *name*.

    Example output::

        --color-primary-50: oklch(0.9710 0.0146 264.05);
        --color-primary-100: oklch(0.9360 0.0311 264.05);
        ...
        --color-primary-950: oklch(0.2360 0.0521 264.05);

    ``name`` should be one of: primary, secondary, accent, info, success,
    danger, warning.
    """
    # If the user passed a CSS variable (e.g. "var(--color-indigo-500)")
    # or a raw property name (e.g. "--color-indigo-500"), prefer to map
    # the generated stops to that variable family instead of attempting
    # to parse the variable's computed colour here.
    v = color.strip()

    # Handle 'var(--foo-500)' or 'var(--foo)'. Extract the inner token and
    # decide whether it encodes a numeric stop at the end.
    if v.lower().startswith('var(') and v.endswith(')'):
        inner = v[v.find('(') + 1 : v.rfind(')')].strip()
        if inner.startswith('--'):
            m_end = re.search(r'-(50|100|200|300|400|500|600|700|800|900|950)$', inner)
            if m_end:
                base = inner[:m_end.start()]
                lines = [f"  --color-{name}-{stop}: var({base}-{stop});" for stop, _ in _STOPS]
            else:
                lines = [f"  --color-{name}-{stop}: var({inner});" for stop, _ in _STOPS]
            return "\n".join(lines)

    # Handle raw property names like --color-indigo-500 or --brand
    if v.startswith('--'):
        m_end = re.search(r'-(50|100|200|300|400|500|600|700|800|900|950)$', v)
        if m_end:
            base = v[:m_end.start()]
            lines = [f"  --color-{name}-{stop}: var({base}-{stop});" for stop, _ in _STOPS]
        else:
            lines = [f"  --color-{name}-{stop}: var({v});" for stop, _ in _STOPS]
        return "\n".join(lines)

    # Fallback: compute an OKLch palette from the provided colour string
    palette = generate_palette(color)
    lines = [f"  --color-{name}-{stop}: {value};" for stop, value in sorted(palette.items())]
    return "\n".join(lines)
