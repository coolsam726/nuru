from typing import TypedDict, Optional


class RadioOption(TypedDict, total=False):
    """TypedDict describing the mapping form accepted by the radio buttons template.

    Keys:
      - value: the form value for the option (string)
      - title / label: display title for the option
      - description / desc: optional description text
      - icon: optional raw SVG/HTML (rendered with |safe)
      - image: optional image URL
    """

    value: str
    title: str
    label: str
    description: str
    desc: str
    icon: str
    image: str
