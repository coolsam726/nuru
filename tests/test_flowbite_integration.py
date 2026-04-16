"""Tests for nuru.integrations.flowbite — standalone datepicker integration."""
import pytest
from nuru import AdminPanel
from nuru.integrations.flowbite import (
    FlowbiteDatepicker,
    FlowbiteDateRangePicker,
    FLOWBITE_JS_CDN,
    register_flowbite,
)


# ---------------------------------------------------------------------------
# Field dataclass defaults
# ---------------------------------------------------------------------------

def test_flowbite_datepicker_defaults():
    f = FlowbiteDatepicker("birth_date", "Date of Birth")
    assert f.key == "birth_date"
    assert f.label == "Date of Birth"
    assert f.field_type == "flowbite_datepicker"
    assert f.date_format == "yyyy-mm-dd"
    assert f.autohide is True
    assert f.buttons is False
    assert f.min_date == ""
    assert f.max_date == ""
    assert f.orientation == "bottom"
    assert f.title == ""


def test_flowbite_datepicker_custom_attrs():
    f = FlowbiteDatepicker(
        "expires",
        "Expiry Date",
        date_format="mm/dd/yyyy",
        autohide=False,
        buttons=True,
        min_date="01/01/2024",
        max_date="12/31/2030",
        orientation="top",
        title="Pick expiry",
    )
    assert f.date_format == "mm/dd/yyyy"
    assert f.autohide is False
    assert f.buttons is True
    assert f.min_date == "01/01/2024"
    assert f.max_date == "12/31/2030"
    assert f.orientation == "top"
    assert f.title == "Pick expiry"


def test_flowbite_daterangepicker_defaults():
    f = FlowbiteDateRangePicker("stay", "Stay Dates")
    assert f.field_type == "flowbite_daterangepicker"
    assert f.start_placeholder == "Start date"
    assert f.end_placeholder == "End date"
    assert f.date_format == "yyyy-mm-dd"


# ---------------------------------------------------------------------------
# register_flowbite
# ---------------------------------------------------------------------------

@pytest.fixture()
def panel():
    return AdminPanel(title="Test Panel", prefix="/admin")


def test_register_adds_cdn(panel):
    register_flowbite(panel)
    assert FLOWBITE_JS_CDN in panel.extra_js


def test_register_is_idempotent(panel):
    register_flowbite(panel)
    register_flowbite(panel)
    assert panel.extra_js.count(FLOWBITE_JS_CDN) == 1


def test_register_adds_template_dir(panel):
    """After registration the Jinja env can locate the datepicker templates."""
    register_flowbite(panel)
    # If the template is missing this raises TemplateNotFound
    panel._jinja_env.get_template("partials/fields/form/flowbite_datepicker.html")
    panel._jinja_env.get_template("partials/fields/form/flowbite_daterangepicker.html")
    panel._jinja_env.get_template("partials/fields/detail/flowbite_datepicker.html")
    panel._jinja_env.get_template("partials/fields/detail/flowbite_daterangepicker.html")


# ---------------------------------------------------------------------------
# Template rendering smoke tests
# ---------------------------------------------------------------------------

def _render_form_field(panel, field, current=None):
    """Render a form field template in isolation and return the HTML string."""
    tmpl = panel._jinja_env.get_template("partials/fields/form/flowbite_datepicker.html")
    return tmpl.render(
        field=field,
        current=current,
        has_error=False,
        errors={},
        input_class="block w-full rounded-lg border border-secondary-300 text-sm",
        panel_prefix="/admin",
    )


def test_form_template_renders_datepicker_attr(panel):
    register_flowbite(panel)
    f = FlowbiteDatepicker("dob", "Date of Birth")
    html = _render_form_field(panel, f)
    assert 'datepicker' in html
    assert 'datepicker-format="yyyy-mm-dd"' in html
    assert 'datepicker-autohide' in html
    assert 'name="dob"' in html


def test_form_template_renders_current_value(panel):
    register_flowbite(panel)
    f = FlowbiteDatepicker("dob", "DOB")
    html = _render_form_field(panel, f, current="1990-06-15")
    assert 'value="1990-06-15"' in html


def test_form_template_no_autohide_when_false(panel):
    register_flowbite(panel)
    f = FlowbiteDatepicker("dob", "DOB", autohide=False)
    html = _render_form_field(panel, f)
    assert 'datepicker-autohide' not in html


def test_form_template_min_max_dates(panel):
    register_flowbite(panel)
    f = FlowbiteDatepicker("d", "D", min_date="2020-01-01", max_date="2030-12-31")
    html = _render_form_field(panel, f)
    assert 'datepicker-min-date="2020-01-01"' in html
    assert 'datepicker-max-date="2030-12-31"' in html
