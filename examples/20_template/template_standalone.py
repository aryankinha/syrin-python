"""Template engine — standalone usage.

- Template with slots (Mustache-style syntax)
- render() with explicit values
- slot_schema() for JSON schema
- from_file, from_string factories
"""

from syrin import SlotConfig, Template


def main() -> None:
    # 1. Simple template
    tpl = Template(
        name="greet",
        content="Hello, {{name}}! You have {{count}} items.",
        slots={
            "name": SlotConfig("str", required=True),
            "count": SlotConfig("int", required=False, default=0),
        },
    )
    print(tpl.render(name="Alice", count=5))
    # Hello, Alice! You have 5 items.

    # 2. With defaults
    print(tpl.render(name="Bob"))
    # Hello, Bob! You have 0 items.

    # 3. Conditional ({{#show}}...{{/show}})
    tpl2 = Template(
        "cond",
        "{{#show}}Visible content{{/show}}",
        slots={"show": SlotConfig("bool")},
    )
    print(tpl2.render(show=True))  # Visible content
    print(tpl2.render(show=False))  # (empty)

    # 4. List iteration ({{#items}}{{.}}{{/items}})
    tpl3 = Template(
        "list",
        "Items: {{#items}}{{.}}, {{/items}}",
        slots={"items": SlotConfig("list[str]")},
    )
    print(tpl3.render(items=["a", "b", "c"]))
    # Items: a, b, c,

    # 5. slot_schema for LLM extraction
    schema = tpl.slot_schema()
    print(schema)
    # {"type": "object", "properties": {...}, "required": ["name"]}


if __name__ == "__main__":
    main()
