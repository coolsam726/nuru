from nuru.fields import Text, Number, Textarea


def test_input_styling_and_convenience_methods():
    t = Text("username")
    t.input_class("px-3 py-2 text-sm").input_style("background: #fff;")
    assert t.get_input_class() == "px-3 py-2 text-sm"
    assert t.get_input_style() == "background: #fff;"


def test_text_max_length_and_number_minmax():
    t = Text("title")
    t.max_length(255)
    assert t.get_max_length() == 255

    n = Number("qty")
    n.min_value(0).max_value(100)
    assert n.get_min_value() == 0
    assert n.get_max_value() == 100


def test_textarea_rows():
    ta = Textarea("bio")
    ta.rows(10)
    assert ta.get_rows() == 10
