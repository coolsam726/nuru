**Radio Buttons (Flowbite-style) — Usage**

This documents the `RadioButtons` component provided by `nuru/components` and the Flowbite-style selectable card template added at `nuru/components/templates/partials/fields/form/radio_buttons.html`.

1) Register the components

Call `register_components(admin_panel)` during app setup so the templates are discoverable (see `example_app/main.py`). If you rely on Flowbite JS/CSS behaviours, also call `register_flowbite(admin_panel)`.

2) Option formats

The template accepts options in three forms:

- Mapping/dict with explicit keys: `value`, `title` (or `label`), optional `description` (or `desc`), optional `icon` (raw SVG/HTML string) or `image` (URL).
- Mapping/dict with explicit keys: `value`, `title` (or `label`), optional `description` (or `desc`), optional `icon` (raw SVG/HTML string) or `image` (URL). The mapping shape is available as a `TypedDict`: `nuru.components.types.RadioOption`.

8) Typing example

You can annotate your options list for static checking. Import the `RadioOption` TypedDict and annotate a variable or function argument:

```py
from typing import List
from nuru.components.types import RadioOption

options: List[RadioOption | tuple[str, str] | str] = [
    {"value": "react", "title": "React Js", "icon": "<svg>...</svg>"},
    ("vue", "Vue Js", "A progressive frontend framework."),
    "angular",
]

def make_field(opts: List[RadioOption | tuple | str]):
    return RadioButtons(name="tech", label="Tech", options=opts)
```

This helps editors and `mypy` understand the expected keys for mapping-style options.
- Iterable/tuple/list: `(value, title)` or `(value, title, description)`.
- Simple scalar: `"value"` — the value is used as the title.

Examples (use in a `Resource` `form_fields`):

```py
from nuru.components import RadioButtons

RadioButtons(
    name="technology",
    label="Choose technology",
    options=[
        # mapping with raw SVG icon
        {
            "value": "react",
            "title": "React Js",
            "description": "A JavaScript library for building user interfaces.",
            "icon": "<svg ...>...</svg>",
        },

        # tuple with title + description
        ("vue", "Vue Js", "A progressive frontend framework."),

        # mapping with an image URL
        {"value": "svelte", "title": "Svelte", "image": "/static/img/svelte.png"},

        # simple scalar
        "angular",
    ],
)
```

Notes:
- The `icon` value is rendered with `|safe` in the template so you can pass raw SVG markup as a Python string. Ensure the SVG is trusted (do not inject untrusted HTML).
- `image` should be a URL/path to an image; the template renders an `<img>` tag.

3) Behavior and accessibility

- Each option renders as a selectable card (radio input with an associated label). The input element is visually hidden and the label is a clickable card styled using Flowbite-like classes.
- The template sets an `id` per option (`<field.key>-<index>`) so labels correctly associate with inputs.
- If `field.required` is truthy, the radio inputs receive the `required` attribute.

4) Customizing markup or classes

If you want to change markup or classes, copy the partial to your app templates directory at the same relative path (`partials/fields/form/radio_buttons.html`) and edit it. Ensure your app template directory is earlier in `template_dirs` so Jinja finds it first.

5) Example: pre-filled / default

The selected option is determined by the field's value on the model instance rendered in the form. For quick testing you can supply the initial value on the model instance used to render the form.

6) Security

- `icon` content is rendered unescaped. Only pass SVG/HTML you control. If you need to render user-supplied svg, sanitize it first.

7) Reference

- Template: [nuru/components/templates/partials/fields/form/radio_buttons.html](nuru/components/templates/partials/fields/form/radio_buttons.html)
- Example usage: [example_app/main.py](example_app/main.py#L1048)
