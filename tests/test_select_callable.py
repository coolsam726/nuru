import pytest

from typing import Any, Callable, List
import nuru.forms as fields
from nuru.resources import Resource
from nuru.panel import AdminPanel


def test_callable_options_rendered_in_form():
    panel = AdminPanel(title="Test", prefix="/test")

    class DummyResource(Resource):
        label = "Dummy"
        label_plural = "Dummies"
        slug = "dummies"

        form_fields = [
            fields.Select("kind").label("Kind").options([
                {"value": "a", "label": "Alpha"},
                {"value": "b", "label": "Beta"},
            ])
        ]

    resource = DummyResource(panel=panel)

    html = panel._render("form.html", {
        "resource": resource,
        "record": None,
        "record_id": None,
        "errors": {},
    })

    assert "Alpha" in html
    assert "Beta" in html
