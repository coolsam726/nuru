from nuru.fields import Section, Text


def test_section_fluent_setters():
    s = Section(fields=[])
    s.title("Contact").footer("All required").cols(2).col_span("full").css_class("p-4")

    assert s.get_title() == "Contact"
    assert s.get_footer() == "All required"
    assert s.get_cols() == 2
    assert s.get_col_span() == "full"
    assert s.get_css_class() == "p-4"


def test_section_defaults():
    s = Section(fields=[])
    assert s.get_title() == ""
    assert s.get_cols() == 1
    assert s.is_styled() is True
    assert s.get_section_type() == "styled"
    assert s.is_section_field() is True
    assert s.is_fieldset() is False


def test_section_unstyled_type():
    s = Section(fields=[], styled=False)
    assert s.get_section_type() == "flat"


def test_section_contains_fields():
    f = Text("name")
    s = Section(fields=[f])
    assert f in s.get_fields()


def test_field_is_not_section():
    f = Text("name")
    assert f.is_section_field() is False
