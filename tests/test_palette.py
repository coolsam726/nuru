"""Tests for nuru.palette — colour palette generation."""

from __future__ import annotations

import re
import pytest
from nuru.palette import (
    parse_color,
    generate_palette,
    palette_css_vars,
    _dynamic_stop_lightnesses,
)


# ---------------------------------------------------------------------------
# _dynamic_stop_lightnesses
# ---------------------------------------------------------------------------

class TestDynamicStopLightnesses:
    def test_500_equals_base(self):
        targets = _dynamic_stop_lightnesses(0.588)
        assert abs(targets[500] - 0.588) < 1e-6

    def test_monotonic_decreasing(self):
        for L_base in [0.3, 0.588, 0.769, 0.85]:
            targets = _dynamic_stop_lightnesses(L_base)
            stops = sorted(targets.keys())
            lightnesses = [targets[s] for s in stops]
            for i in range(len(lightnesses) - 1):
                assert lightnesses[i] > lightnesses[i + 1], (
                    f"L_base={L_base}: stop {stops[i]} ({lightnesses[i]:.3f}) "
                    f"should be lighter than {stops[i+1]} ({lightnesses[i+1]:.3f})"
                )

    def test_50_near_097(self):
        targets = _dynamic_stop_lightnesses(0.588)
        assert abs(targets[50] - 0.97) < 1e-6

    def test_950_near_020(self):
        targets = _dynamic_stop_lightnesses(0.588)
        assert abs(targets[950] - 0.20) < 1e-6

    def test_all_11_stops_present(self):
        targets = _dynamic_stop_lightnesses(0.5)
        assert set(targets.keys()) == {50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950}

    def test_very_light_input_still_monotonic(self):
        targets = _dynamic_stop_lightnesses(0.90)
        stops = sorted(targets.keys())
        lightnesses = [targets[s] for s in stops]
        for i in range(len(lightnesses) - 1):
            assert lightnesses[i] > lightnesses[i + 1]

    def test_very_dark_input_still_monotonic(self):
        targets = _dynamic_stop_lightnesses(0.25)
        stops = sorted(targets.keys())
        lightnesses = [targets[s] for s in stops]
        for i in range(len(lightnesses) - 1):
            assert lightnesses[i] > lightnesses[i + 1]


# ---------------------------------------------------------------------------
# palette_css_vars — literal color input
# ---------------------------------------------------------------------------

class TestPaletteCssVarsLiteral:
    """For literal color inputs, palette_css_vars should:
    - Register the raw color as --color-{name}
    - Use color-mix() for all 11 stops anchored at the input's actual lightness
    - 500 stop = var(--color-{name}) exactly (the input color unchanged)
    """

    def _parse_vars(self, css: str) -> dict[str, str]:
        """Return {prop: value} from CSS custom property lines."""
        return {
            m.group(1): m.group(2).strip()
            for m in re.finditer(r'--color-(\S+?):\s*(.+?);', css)
        }

    def test_base_var_is_registered(self):
        css = palette_css_vars("primary", "oklch(0.769 0.188 70.08)")
        assert "--color-primary:" in css

    def test_base_var_contains_raw_value(self):
        css = palette_css_vars("primary", "oklch(0.769 0.188 70.08)")
        assert "oklch(0.769 0.188 70.08)" in css

    def test_500_stop_is_base_var(self):
        css = palette_css_vars("primary", "oklch(0.769 0.188 70.08)")
        props = self._parse_vars(css)
        assert props["primary-500"] == "var(--color-primary)"

    def test_500_stop_is_base_var_for_hex(self):
        css = palette_css_vars("primary", "#6366f1")
        assert "var(--color-primary)" in css
        props = self._parse_vars(css)
        assert props["primary-500"] == "var(--color-primary)"

    def test_all_11_stops_present(self):
        css = palette_css_vars("primary", "#3b82f6")
        props = self._parse_vars(css)
        for stop in [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]:
            assert f"primary-{stop}" in props, f"Missing --color-primary-{stop}"

    def test_lighter_stops_use_white_mix(self):
        css = palette_css_vars("primary", "oklch(0.50 0.20 250)")
        # 50 stop should lighten — mix with white
        assert "white" in css

    def test_darker_stops_use_black_mix(self):
        css = palette_css_vars("primary", "oklch(0.50 0.20 250)")
        # 950 stop should darken — mix with black
        assert "black" in css

    def test_uses_color_mix_not_hardcoded_oklch(self):
        """Ensures the literal-input path no longer emits precomputed oklch
        values with the wrong lightness anchor (the old bug)."""
        css = palette_css_vars("primary", "oklch(0.769 0.188 70.08)")
        props = self._parse_vars(css)
        # All derived stops should use color-mix, not bare oklch()
        for stop in [50, 100, 200, 300, 400, 600, 700, 800, 900, 950]:
            val = props[f"primary-{stop}"]
            assert val.startswith("color-mix("), (
                f"--color-primary-{stop} should use color-mix(), got: {val!r}"
            )

    def test_high_lightness_input_500_equals_input(self):
        """Bright amber (L≈0.837) should anchor the 500 stop at itself."""
        css = palette_css_vars("accent", "oklch(0.837 0.164 84.42)")
        props = self._parse_vars(css)
        # The raw color must be registered
        assert "--color-accent:" in css
        assert "oklch(0.837 0.164 84.42)" in css
        # 500 stop must be the base var, not a color-mix
        assert props["accent-500"] == "var(--color-accent)"

    def test_low_lightness_input_still_correct(self):
        """Dark indigo (L≈0.424) should also anchor 500 to itself."""
        css = palette_css_vars("primary", "oklch(0.424 0.181 265.64)")
        props = self._parse_vars(css)
        assert props["primary-500"] == "var(--color-primary)"

    def test_hex_input_supported(self):
        css = palette_css_vars("primary", "#6366f1")
        assert "--color-primary:" in css
        assert "--color-primary-50:" in css

    def test_oklch_percentage_lightness_parsed_correctly(self):
        """oklch(76.9% ...) must be parsed as L=0.769, not L=76.9."""
        pct_css  = palette_css_vars("primary", "oklch(76.9% 0.188 70.08)")
        dec_css  = palette_css_vars("primary", "oklch(0.769 0.188 70.08)")
        # Both should produce the same --color-primary-500 value
        def get_500(css):
            m = re.search(r'--color-primary-500:\s*(.+?);', css)
            return m.group(1).strip() if m else None
        assert get_500(pct_css) == get_500(dec_css)


# ---------------------------------------------------------------------------
# palette_css_vars — var() input (existing behaviour must be preserved)
# ---------------------------------------------------------------------------

class TestPaletteCssVarsVar:
    def test_palette_alias_pattern_detected(self):
        """var(--color-amber-500) should alias to var(--color-amber-{stop}) for all stops."""
        css = palette_css_vars("primary", "var(--color-amber-500)")
        assert "--color-primary-50: var(--color-amber-50);" in css
        assert "--color-primary-500: var(--color-amber-500);" in css
        assert "--color-primary-950: var(--color-amber-950);" in css

    def test_palette_alias_covers_all_11_stops(self):
        css = palette_css_vars("primary", "var(--color-indigo-500)")
        for stop in [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]:
            assert f"--color-primary-{stop}: var(--color-indigo-{stop});" in css

    def test_dash_dash_prefix_alias(self):
        css = palette_css_vars("primary", "--color-indigo-500")
        assert "--color-primary-50: var(--color-indigo-50);" in css
        assert "--color-primary-500: var(--color-indigo-500);" in css

    def test_no_color_mix_for_alias(self):
        """Direct alias path must NOT use color-mix (that was the bug)."""
        css = palette_css_vars("primary", "var(--color-amber-500)")
        assert "color-mix" not in css

    def test_circular_alias_falls_back_to_color_mix(self):
        """var(--color-primary-500) must not generate self-referencing vars."""
        css = palette_css_vars("primary", "var(--color-primary-500)")
        assert "color-mix" in css
        assert "--color-primary-50: var(--color-primary-50);" not in css

    def test_generic_var_uses_color_mix(self):
        """A var() that doesn't match --color-{name}-{stop} falls back to color-mix."""
        css = palette_css_vars("primary", "var(--my-brand-color)")
        assert "color-mix" in css

    def test_var_input_uses_color_mix(self):
        css = palette_css_vars("primary", "var(--my-custom)")
        assert "color-mix" in css

    def test_dash_dash_prefix_expanded(self):
        css = palette_css_vars("primary", "--color-indigo-500")
        # Result should be direct alias, not color-mix
        assert "var(--color-indigo-50)" in css


# ---------------------------------------------------------------------------
# generate_palette (legacy function, keep working)
# ---------------------------------------------------------------------------

class TestGeneratePalette:
    def test_returns_all_stops(self):
        palette = generate_palette("#3b82f6")
        assert set(palette.keys()) == {50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950}

    def test_values_are_oklch_strings(self):
        palette = generate_palette("#6366f1")
        for v in palette.values():
            assert v.startswith("oklch(")

