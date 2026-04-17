"""Tests for nuru.integrations.flowbite — standalone datepicker integration."""
import pytest
from nuru import AdminPanel
from nuru.integrations.flowbite import (
    FlowbiteDatepicker,
    FlowbiteDateRangePicker,
    FLOWBITE_JS_CDN,
    register_flowbite,
)


def test_flowbite_datepicker_defaults():
    f = FlowbiteDatepicker("birth_date")
    assert f.get_key() == "birth_date"
    assert f.get_label() == "Birth Date"
    assert f.get_field_type() == "flowbite_datepicker"
    assert f.get_date_format() == "yyyy-mm-dd"
    assert f.is_autohide() is True
    assert f.has_buttons() is False
    assert f.get_min_date() == ""
    assert f.get_max_date() == ""
    assert f.get_orientation() == "bottom"
    assert f.get_picker_title() == ""


def test_flowbite_datepicker_fluent_setters():
    f = FlowbiteDatepicker("expires").label("Expiry Date")
    f.date_format("mm/dd/yyyy").autohide(False).buttons(True)
    f.min_date("01/01/2024").max_date("12/31/2030")
    f.orientation("top").picker_title("Pick expiry")

    assert f.get_label() == "Expiry Date"
    assert f.get_date_format() == "mm/dd/yyyy"
    assert f.is_autohide() is False
    assert f.has_buttons() is True
    assert f.get_min_date() == "01/01/2024"
    assert f.get_max_date() == "12/31/2030"
    assert f.get_orientation() == "top"
    assert f.get_picker_title() == "Pick expiry"


def test_flowbite_daterangepicker_defaults():
    f = FlowbiteDateRangePicker("stay")
    assert f.get_field_type() == "flowbite_daterangepicker"
    assert f.get_start_placeholder() == "Start date"
    assert f.get_end_placeholder() == "End date"
    assert f.get_date_format() == "yyyy-mm-dd"


def test_flowbite_daterangepicker_fluent_setters():
    f = FlowbiteDateRangePicker("stay")
    f.start_placeholder("Check-in").end_placeholder("Check-out")
    assert f.get_start_placeholder() == "Check-in"
    assert f.get_end_placeholder() == "Check-out"


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
    # Just ensure no exception is raised when looking up the template.
    try:
        panel._jinja_env.get_template("partials/fields/form/flowbite_datepicker.html")
    except Exception:
        pass  # Template may not exist yet; just test registration succeeds
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
    f = FlowbiteDatepicker("dob").label("Date of Birth")
    html = _render_form_field(panel, f)
    assert 'datepicker' in html
    assert 'datepicker-format="yyyy-mm-dd"' in html
    assert 'datepicker-autohide' in html
    assert 'name="dob"' in html


def test_form_template_renders_current_value(panel):
    register_flowbite(panel)
    f = FlowbiteDatepicker("dob").label("DOB")
    html = _render_form_field(panel, f, current="1990-06-15")
    assert 'value="1990-06-15"' in html


def test_form_template_no_autohide_when_false(panel):
    register_flowbite(panel)
    f = FlowbiteDatepicker("dob").label("DOB").autohide(False)
    html = _render_form_field(panel, f)
    assert 'datepicker-autohide' not in html


def test_form_template_min_max_dates(panel):
    register_flowbite(panel)
    f = FlowbiteDatepicker("d").label("D").min_date("2020-01-01").max_date("2030-12-31")
    html = _render_form_field(panel, f)
    assert 'datepicker-min-date="2020-01-01"' in html
    assert 'datepicker-max-date="2030-12-31"' in html
