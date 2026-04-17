"""Tests for DatePicker, DateTimePicker, TimePicker fields."""
import pytest
from nuru.forms import DatePicker, DateTimePicker, TimePicker
from nuru.integrations.flowbite import FlowbiteDatepicker, DateRangePicker


# ---------------------------------------------------------------------------
# DatePicker
# ---------------------------------------------------------------------------

def test_datepicker_defaults():
    f = DatePicker("birth_date")
    assert f.get_key() == "birth_date"
    assert f.get_label() == "Birth Date"
    assert f.get_field_type() == "datepicker"
    assert f.get_date_format() == "yyyy-mm-dd"
    assert f.is_autohide() is True
    assert f.has_buttons() is False
    assert f.get_orientation() == "bottom"
    assert f.get_picker_title() == ""
    assert f.get_min_date() == ""
    assert f.get_max_date() == ""


def test_datepicker_fluent_setters():
    f = (
        DatePicker("expires")
        .label("Expiry Date")
        .date_format("mm/dd/yyyy")
        .autohide(False)
        .buttons(True)
        .orientation("top")
        .picker_title("Pick a date")
        .min_date("01/01/2024")
        .max_date("12/31/2030")
    )
    assert f.get_label() == "Expiry Date"
    assert f.get_date_format() == "mm/dd/yyyy"
    assert f.is_autohide() is False
    assert f.has_buttons() is True
    assert f.get_orientation() == "top"
    assert f.get_picker_title() == "Pick a date"
    assert f.get_min_date() == "01/01/2024"
    assert f.get_max_date() == "12/31/2030"


def test_datepicker_is_section_field_false():
    assert DatePicker("d").is_section_field() is False


def test_flowbite_datepicker_is_datepicker_subclass():
    """FlowbiteDatepicker inherits from DatePicker (backward compat)."""
    f = FlowbiteDatepicker("d")
    assert isinstance(f, DatePicker)
    # Keeps its own field_type for template resolution
    assert f.get_field_type() == "flowbite_datepicker"


# ---------------------------------------------------------------------------
# DateTimePicker
# ---------------------------------------------------------------------------

def test_datetimepicker_defaults():
    f = DateTimePicker("event_at")
    assert f.get_key() == "event_at"
    assert f.get_label() == "Event At"
    assert f.get_field_type() == "datetimepicker"
    assert f.get_date_format() == "yyyy-mm-dd"
    assert f.get_time_format() == "HH:mm"
    assert f.is_autohide() is True
    assert f.has_buttons() is False
    assert f.get_min_date() == ""
    assert f.get_max_date() == ""
    assert f.get_min_time() == ""
    assert f.get_max_time() == ""


def test_datetimepicker_fluent_setters():
    f = (
        DateTimePicker("scheduled")
        .label("Scheduled at")
        .date_format("dd/mm/yyyy")
        .time_format("hh:mm a")
        .autohide(False)
        .buttons(True)
        .min_date("2024-01-01")
        .max_date("2030-12-31")
        .min_time("08:00")
        .max_time("18:00")
    )
    assert f.get_label() == "Scheduled at"
    assert f.get_date_format() == "dd/mm/yyyy"
    assert f.get_time_format() == "hh:mm a"
    assert f.is_autohide() is False
    assert f.has_buttons() is True
    assert f.get_min_date() == "2024-01-01"
    assert f.get_max_date() == "2030-12-31"
    assert f.get_min_time() == "08:00"
    assert f.get_max_time() == "18:00"


# ---------------------------------------------------------------------------
# TimePicker
# ---------------------------------------------------------------------------

def test_timepicker_defaults():
    f = TimePicker("opens_at")
    assert f.get_key() == "opens_at"
    assert f.get_label() == "Opens At"
    assert f.get_field_type() == "timepicker"
    assert f.get_min_time() == ""
    assert f.get_max_time() == ""
    assert f.get_step() == 0


def test_timepicker_fluent_setters():
    f = (
        TimePicker("slot")
        .label("Time slot")
        .min_time("08:00")
        .max_time("18:00")
        .step(900)
    )
    assert f.get_label() == "Time slot"
    assert f.get_min_time() == "08:00"
    assert f.get_max_time() == "18:00"
    assert f.get_step() == 900


def test_timepicker_is_section_field_false():
    assert TimePicker("t").is_section_field() is False


# ---------------------------------------------------------------------------
# DateRangePicker
# ---------------------------------------------------------------------------

def test_daterangepicker_defaults():
    f = DateRangePicker("stay")
    assert f.get_field_type() == "flowbite_daterangepicker"
    assert f.get_start_placeholder() == "Start date"
    assert f.get_end_placeholder() == "End date"
    assert f.get_date_format() == "yyyy-mm-dd"
    assert isinstance(f, DatePicker)


def test_daterangepicker_fluent_setters():
    f = DateRangePicker("period").start_placeholder("From").end_placeholder("To")
    assert f.get_start_placeholder() == "From"
    assert f.get_end_placeholder() == "To"
