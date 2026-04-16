**Nuru Components (Flowbite-backed) — Usage**

This module provides a small set of Flowbite-styled form/detail components packaged under `nuru.components`.

- **Purpose:** Add optional, drop-in components (Radio, Toggle, RadioButtons, Timepicker) with their own templates.
- **Templates:** placed under `nuru/components/templates/partials/fields/` and registered via `register_components(panel)`.

**Registering**

Call `register_components` once when configuring your `AdminPanel` so the templates are discoverable by the Jinja loader. Example (edit your app bootstrap before mounting the panel):

```py
from nuru.components import register_components

# ... create admin_panel as usual ...
register_components(admin_panel)
register_flowbite(admin_panel)  # optional: loads Flowbite JS/CSS if you use Flowbite behaviours
admin_panel.mount(app)
```

Place the `register_components` call before `admin_panel.mount(app)` so templates are available when the panel renders pages.

**Importing component classes**

You can import the component field classes and use them directly in a `Resource`'s `fields` definition:

```py
from nuru import Resource, fields
from nuru.components import Timepicker, Radio, Toggle, RadioButtons

class EventResource(Resource):
    model = Event
    fields = [
        fields.Text("title", label="Event"),
        Timepicker(name="start_time", label="Start time"),
        Radio(name="status", label="Status", options=[("draft","Draft"),("pub","Published")]),
    ]

```

Typing: if you use static typing you can import `RadioOption` from `nuru.components.types` to annotate mapping-style options passed to `Radio`/`RadioButtons`.

These classes subclass the library's `Field` base and behave like other `nuru` fields (they render form and detail partials, support `help` and `required` attributes, etc.).

**Flowbite integration**

- If you want Flowbite's JS behaviours (for example: datepickers, dropdowns), call `register_flowbite(admin_panel)` as shown above. `register_flowbite` will add the Flowbite CDN `extra_js` and register the Flowbite templates.
- The components in `nuru.components` are primarily template-backed. For richer client behaviour (time pickers, enhanced toggles), wire in Flowbite or another JS library and add a tiny initializer script if needed.

**Customising templates**

If you want to change the markup or classes for these components, copy the partial you want to override into your app's template directory and place it at the same relative path (`partials/fields/form/<component>.html` or `partials/fields/detail/<component>.html`). Ensure your app's template directory is earlier in `template_dirs` so Jinja finds it first.

**Example: enabling in example app**

Edit `example_app/main.py` and add:

```py
from nuru.components import register_components
from nuru.integrations.flowbite import register_flowbite

register_components(admin_panel)
register_flowbite(admin_panel)  # optional

# then mount as usual
admin_panel.mount(app)
```

That's it — the components will render using their templates and can be used in `Resource` field lists.

**Notes**

- These components are opt-in. If you do not call `register_components(panel)` their templates will not be discovered and rendering will fall back to the default field templates.
- If you rely on Flowbite runtime behaviour, ensure `register_flowbite(panel)` is called so the Flowbite JS is loaded.
