from nuru.forms import Text


def test_fluent_chaining_returns_self():
    t = Text("email")
    result = t.label("E-mail").required().placeholder("you@example.com")
    # Fluent setters mutate in place and return self
    assert result is t
    assert t.get_label() == "E-mail"
    assert t.is_required() is True
    assert t.get_placeholder() == "you@example.com"


def test_field_defaults_on_new_instance():
    a = Text("email")
    b = Text("email")
    # Mutating one should not affect another (separate instances)
    a.required()
    assert a.is_required() is True
    assert b.is_required() is False


def test_field_chaining_multiple_validators():
    t = Text("age")
    t.numeric().integer()
    assert "numeric" in t.get_validators()
    assert "integer" in t.get_validators()


def test_email_convenience_sets_input_type_and_validator():
    t = Text("email")
    t.email()
    assert t.get_input_type() == "email"
    assert "email" in t.get_validators()


def test_optional_reverses_required():
    t = Text("name")
    t.required().optional()
    assert t.is_required() is False
