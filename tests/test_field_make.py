from nuru.forms import Text, Number


def test_make_returns_field_instance():
    t = Text("email")
    t.label("Email Address").required().email()
    assert t.get_label() == "Email Address"
    assert t.is_required() is True
    assert "email" in t.get_validators()
    assert t.get_input_type() == "email"


def test_auto_label_from_key():
    t = Text("first_name")
    assert t.get_label() == "First Name"


def test_number_min_max():
    n = Number("qty")
    n.min_value(1).max_value(10)
    assert n.get_min_value() == 1
    assert n.get_max_value() == 10


def test_chaining_is_fluent():
    t = Text("slug")
    result = t.label("Slug").placeholder("my-slug").help_text("URL-safe identifier")
    assert result is t
    assert t.get_label() == "Slug"
    assert t.get_placeholder() == "my-slug"
    assert t.get_help_text() == "URL-safe identifier"
