from __future__ import annotations

from dataclasses import replace, asdict
from typing import Any


class FieldBuilder:
    """Immutable builder that wraps a Field dataclass and provides
    Filament-style fluent methods (without requiring a final .build()).

    The builder returns new FieldBuilder instances on each fluent call and
    delegates attribute access to the wrapped dataclass so it can be used
    interchangeably in template rendering and code that reads field attrs.
    """

    def __init__(self, field: Any):
        self._field = field

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"FieldBuilder({self._field!r})"

    def _replace(self, **kwargs) -> "FieldBuilder":
        """Attempt dataclasses.replace, fall back to asdict-based construction
        so callers can set attributes that may not exist on every Field subclass.
        """
        # Map public names to private underscored attributes when present.
        # Only include keys that exist in the dataclass __dict__ to avoid
        # accidentally calling the constructor with InitVar names in the
        # wrong order (which breaks the dataclass invariants).
        current_fields = set(vars(self._field).keys())
        mapped = {}
        for k, v in kwargs.items():
            if k in current_fields:
                mapped[k] = v
            else:
                underscored = f"_{k}"
                if underscored in current_fields:
                    mapped[underscored] = v

        # Use dataclasses.replace which preserves dataclass invariants; if it
        # fails due to an unexpected key, raise so callers can see the error.
        return FieldBuilder(replace(self._field, **mapped))

    # Fluent methods (examples). These should mirror the replace-based
    # methods available on the dataclass itself (they create a new dataclass
    # instance and wrap it in a new builder).
    def required(self, yes: bool = True) -> "FieldBuilder":
        return self._replace(required=yes)

    def placeholder(self, text: str) -> "FieldBuilder":
        return self._replace(placeholder=text)

    def email(self) -> "FieldBuilder":
        # Ensure validators are taken from the current wrapped Field and then
        # set on the new instance with input_type updated.
        validators = list(getattr(self._field, "_validators", []) or []) + ["email"]
        return self._replace(input_type="email")._replace(validators=validators)

    def numeric(self) -> "FieldBuilder":
        validators = list(getattr(self._field, "validators", []) or []) + ["numeric"]
        return self._replace(validators=validators)

    def integer(self) -> "FieldBuilder":
        validators = list(getattr(self._field, "validators", []) or []) + ["integer"]
        return self._replace(validators=validators)

    def password(self) -> "FieldBuilder":
        return self._replace(input_type="password")

    def tel(self) -> "FieldBuilder":
        return self._replace(input_type="tel")

    def url(self) -> "FieldBuilder":
        f = self._replace(input_type="url")._field
        validators = list(getattr(f, "validators", []) or []) + ["url"]
        return self._replace(validators=validators)

    # Styling helpers
    def input_class(self, classes: str) -> "FieldBuilder":
        return self._replace(input_class=classes)

    def input_style(self, style: str) -> "FieldBuilder":
        return self._replace(input_style=style)

    # Section-like helpers (proxy to section fields where applicable)
    def title(self, text: str) -> "FieldBuilder":
        return self._replace(label=text)

    # Help / hint text shown alongside the field
    def help(self, text: str) -> "FieldBuilder":
        return self._replace(help_text=text)

    def hint(self, text: str) -> "FieldBuilder":
        return self.help(text)

    # Accessibility / visibility helpers
    def disabled(self, on: bool = True) -> "FieldBuilder":
        return self._replace(disabled=on)

    def readonly(self, on: bool = True) -> "FieldBuilder":
        return self._replace(readonly=on)

    def visible(self, on: bool = True) -> "FieldBuilder":
        return self._replace(visible=on)

    def hidden(self) -> "FieldBuilder":
        return self._replace(visible=False)

    # Layout helpers
    def cols(self, n: int) -> "FieldBuilder":
        return self._replace(cols=n)

    def col_span(self, span: int) -> "FieldBuilder":
        return self._replace(col_span=span)

    def css_class(self, css: str) -> "FieldBuilder":
        return self._replace(css_class=css)

    def styled(self, on: bool = True) -> "FieldBuilder":
        return self._replace(styled=on)

    # Additional Filament-like helpers
    def default(self, value: Any) -> "FieldBuilder":
        return self._replace(default=value)

    def nullable(self, on: bool = True) -> "FieldBuilder":
        return self._replace(nullable=on)

    def reactive(self, on: bool = True) -> "FieldBuilder":
        return self._replace(reactive=on)

    def prefix(self, text: str) -> "FieldBuilder":
        return self._replace(prefix=text)

    def suffix(self, text: str) -> "FieldBuilder":
        return self._replace(suffix=text)

    def prefix_icon(self, name: str) -> "FieldBuilder":
        return self._replace(prefix_icon=name)

    def suffix_icon(self, name: str) -> "FieldBuilder":
        return self._replace(suffix_icon=name)

    def autofocus(self, on: bool = True) -> "FieldBuilder":
        return self._replace(autofocus=on)

    def autocomplete(self, value: str) -> "FieldBuilder":
        return self._replace(autocomplete=value)

    def max_length(self, n: int) -> "FieldBuilder":
        return self._replace(max_length=n)

    # Delegate attribute access to the wrapped dataclass
    def __getattr__(self, name: str) -> Any:
        return getattr(self._field, name)

    # Equality delegates to wrapped field equality
    def __eq__(self, other: object) -> bool:  # pragma: no cover - trivial
        if isinstance(other, FieldBuilder):
            return self._field == other._field
        return self._field == other
