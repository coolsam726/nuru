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
    """
    distance = abs(L_target - L_base)
    factor = max(0.0, 1.0 - distance / 0.70)
    return C_base * factor


def generate_palette(color: str) -> dict[int, str]:
    """Generate a {stop: oklch_string} palette from any CSS colour.

    Returns a dict mapping stop numbers (50, 100, …, 950) to CSS oklch()
    strings ready to embed in a stylesheet.

    .. note::
        This function uses fixed lightness targets anchored at L≈0.588 for the
        500 stop.  It works well when the input colour has lightness close to
        0.588.  For colours at other lightness levels (e.g. bright amber at
        L≈0.84) prefer ``palette_css_vars`` which anchors at the actual input
        lightness and uses ``color-mix()`` for perceptually correct results.
    """
    base = parse_color(color)
    result: dict[int, str] = {}
    for stop, L_target in _STOPS:
        C_target = _scale_chroma(base.C, base.L, L_target)
        result[stop] = f"oklch({L_target:.4f} {C_target:.4f} {base.H:.2f})"
    return result


def _dynamic_stop_lightnesses(L_base: float) -> dict[int, float]:
    """Return 50-950 lightness targets anchored at *L_base* for the 500 stop.

    The 5 lighter stops (400→50) spread evenly from L_base up to 0.97.
    The 5 darker stops (600→950) spread evenly from L_base down to 0.20.
    The 500 stop is exactly L_base.

    This ensures:
    - The generated 500 stop matches the input colour precisely.
    - The scale is always monotonic (50 is always lightest, 950 always darkest).
    - The progression is perceptually smooth regardless of where in the
      lightness range the input colour sits.
    """
    L_MIN, L_MAX = 0.20, 0.97
    # Clamp to avoid degenerate single-sided scales
    L_base = max(L_MIN + 0.01, min(L_MAX - 0.01, L_base))

    # Lighter steps listed closest-to-base first so `step` increments outward
    lighter = [400, 300, 200, 100, 50]
    darker  = [600, 700, 800, 900, 950]
    n = len(lighter)  # == len(darker) == 5

    targets: dict[int, float] = {500: L_base}
    for step, stop in enumerate(lighter, 1):
        targets[stop] = L_base + (step / n) * (L_MAX - L_base)
    for step, stop in enumerate(darker, 1):
        targets[stop] = L_base - (step / n) * (L_base - L_MIN)
    return targets


def palette_css_vars(name: str, color: str) -> str:
    """Return a block of CSS custom property declarations for *name*.

    ``name`` should be one of: ``primary``, ``secondary``, ``accent``,
    ``info``, ``success``, ``danger``, ``warning``.

    ``color`` may be any of:

    * A real CSS colour string — ``#6366f1``, ``oklch(0.769 0.188 70.08)``,
      ``rgb(99 102 241)``, ``hsl(239 84% 67%)``.  The colour is taken as the
      **500 anchor**; the full 50–950 scale is derived proportionally around
      its actual lightness using ``color-mix(in oklch, …)``.

    * A CSS custom-property reference — ``var(--color-indigo-500)`` or
      ``--color-indigo-500``.

      If the token follows the ``--color-{palette}-{stop}`` naming convention
      (e.g. ``var(--color-amber-500)``), every stop is aliased directly to the
      corresponding stop of that palette
      (``--color-primary-50: var(--color-amber-50)`` etc.).  This is exact —
      no colour math is involved and the browser resolves the full palette at
      paint time.

      For arbitrary variable names that don't match the pattern, a
      ``color-mix()`` fallback anchored at L≈0.588 is used instead (less
      accurate; prefer the palette-alias form when possible).

    Why ``color-mix()`` instead of precomputed ``oklch()`` values
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Tailwind v4 parses ``oklch()`` values in ``@theme`` blocks to extract
    channel data for its opacity-modifier utilities.  Its parser reads the
    first token numerically and **drops the ``%`` unit**, so
    ``oklch(76.9% 0.188 70.08)`` is stored with lightness = 76.9 (not 0.769),
    which breaks every opacity utility that touches that colour.  Using
    ``color-mix()`` delegates all colour arithmetic to the browser, which
    handles all CSS Color Level 4 notations correctly.
    """
    v = color.strip()

    # ── CSS variable input ────────────────────────────────────────────────
    if v.lower().startswith("var(") and v.endswith(")"):
        inner = v[4:-1].strip()          # content inside var(…)
        base_token = v
    elif v.startswith("--"):
        inner = v
        base_token = f"var({v})"
    else:
        inner = ""
        base_token = ""

    if inner:
        # Fast path: --color-{palette}-{stop} pattern → alias every stop
        # directly to the same palette.  This is exact: no colour-math, no
        # lightness assumptions — the browser already has the right values.
        # Example: var(--color-amber-500) → --color-primary-50: var(--color-amber-50)
        _alias_re = re.compile(r'^--color-([a-z][\w-]*)-\d+$', re.I)
        m = _alias_re.match(inner)
        if m:
            src_palette = m.group(1)
            if src_palette != name:          # guard against circular self-alias
                lines = [
                    f"  --color-{name}-{stop}: var(--color-{src_palette}-{stop});"
                    for stop, _ in _STOPS
                ]
                return "\n".join(lines)
            # src_palette == name → fall through to color-mix to avoid
            # circular references like --color-primary-50: var(--color-primary-50)

        # Generic var() fallback: colour-mix anchored at assumed L=0.588.
        # Works best when the referenced colour is already near the 500-level
        # lightness.  Users should prefer the palette-alias pattern above for
        # accurate results.
        base_lightness = dict(_STOPS)[500]
        # (base_token already set above)

    if not inner:
        # ── Literal colour input ──────────────────────────────────────────
        # Parse the colour to find its actual lightness, then anchor the 500
        # stop at that lightness and spread the rest proportionally.
        try:
            parsed = parse_color(v)
        except ValueError:
            # Last-resort fallback: fixed-lightness oklch strings
            palette = generate_palette(v)
            lines = [f"  --color-{name}-{stop}: {value};" for stop, value in sorted(palette.items())]
            return "\n".join(lines)

        base_lightness = parsed.L
        base_token = f"var(--color-{name})"

        # Build dynamic stop targets anchored at the actual input lightness
        stop_targets = _dynamic_stop_lightnesses(base_lightness)

        def mix_expr_literal(stop: int, L_target: float) -> str:
            if abs(L_target - base_lightness) < 1e-6:
                return base_token  # exact match → the input colour itself
            if L_target > base_lightness:
                base_pct = max(0.0, min(100.0,
                    (1.0 - L_target) / (1.0 - base_lightness) * 100.0))
                return f"color-mix(in oklch, white {100.0 - base_pct:.2f}%, {base_token} {base_pct:.2f}%)"
            base_pct = max(0.0, min(100.0,
                L_target / base_lightness * 100.0))
            return f"color-mix(in oklch, black {100.0 - base_pct:.2f}%, {base_token} {base_pct:.2f}%)"

        lines = [f"  --color-{name}: {v};"]  # register the base colour
        for stop in [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]:
            L_target = stop_targets[stop]
            lines.append(f"  --color-{name}-{stop}: {mix_expr_literal(stop, L_target)};")
        return "\n".join(lines)

    # ── Shared color-mix path for var() inputs ────────────────────────────
    def mix_expr_var(L_target: float) -> str:
        if abs(L_target - base_lightness) < 1e-6:
            return base_token
        if L_target > base_lightness:
            base_pct = max(0.0, min(100.0,
                (1.0 - L_target) / (1.0 - base_lightness) * 100.0))
            return f"color-mix(in oklch, white {100.0 - base_pct:.2f}%, {base_token} {base_pct:.2f}%)"
        base_pct = max(0.0, min(100.0, L_target / base_lightness * 100.0))
        return f"color-mix(in oklch, black {100.0 - base_pct:.2f}%, {base_token} {base_pct:.2f}%)"

    lines = [f"  --color-{name}-{stop}: {mix_expr_var(L_target)};" for stop, L_target in _STOPS]
    return "\n".join(lines)


_UTILITY_STOPS: list[int] = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]


def palette_utility_css(names: list[str]) -> str:
    """Return CSS utility class rules for every semantic colour name and stop.

    For each name in *names* and each shade stop (50–950), emits four rules::

        .bg-primary-500   { background-color: var(--color-primary-500); }
        .text-primary-500 { color:             var(--color-primary-500); }
        .border-primary-500 { border-color:    var(--color-primary-500); }
        .ring-primary-500   { --tw-ring-color: var(--color-primary-500); }

    These classes reference the CSS custom properties generated by
    ``palette_css_vars`` and injected into the page ``<style>`` block at
    runtime, so they work regardless of the Tailwind build step.
    """
    lines: list[str] = []
    for name in names:
        for stop in _UTILITY_STOPS:
            var = f"var(--color-{name}-{stop})"
            lines.append(f"    .bg-{name}-{stop} {{ background-color: {var}; }}")
            lines.append(f"    .text-{name}-{stop} {{ color: {var}; }}")
            lines.append(f"    .border-{name}-{stop} {{ border-color: {var}; }}")
            lines.append(f"    .ring-{name}-{stop} {{ --tw-ring-color: {var}; }}")
    return "\n".join(lines)
