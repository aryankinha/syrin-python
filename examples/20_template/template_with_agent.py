"""Template + Agent — output_config with template.

- output_config=OutputConfig(format=..., template=...)
- output=Output(MyModel) required when template is set
- response.content = rendered template
- response.template_data = slot values used
"""

from pydantic import BaseModel

from syrin import Agent, Model, Output, OutputConfig, OutputFormat, SlotConfig, Template


class CapitalData(BaseModel):
    """Extracted capital structure fields."""

    authorized_shares: int
    face_value: str
    authorized_capital: str
    issued_shares: int
    issued_capital: str


def main() -> None:
    template = Template(
        name="capital_structure",
        content="""
CAPITAL STRUCTURE

A) AUTHORISED SHARE CAPITAL
   {{authorized_shares}} Equity Shares of face value ₹{{face_value}} each
   ₹{{authorized_capital}}

B) ISSUED, SUBSCRIBED AND PAID-UP SHARE CAPITAL
   {{issued_shares}} Equity Shares of face value ₹{{face_value}} each
   ₹{{issued_capital}}
""",
        slots={
            "authorized_shares": SlotConfig("int", required=True),
            "face_value": SlotConfig("str", required=True),
            "authorized_capital": SlotConfig("str", required=True),
            "issued_shares": SlotConfig("int", required=True),
            "issued_capital": SlotConfig("str", required=True),
        },
    )

    agent = Agent(
        model=Model.Almock(
            response_mode="custom",
            custom_response='{"authorized_shares": 5000000, "face_value": "10", '
            '"authorized_capital": "5,00,00,000", "issued_shares": 2000000, '
            '"issued_capital": "2,00,00,000"}',
            latency_min=0,
            latency_max=0,
        ),
        system_prompt="Extract capital structure. Return JSON.",
        output=Output(CapitalData),
        output_config=OutputConfig(format=OutputFormat.TEXT, template=template),
    )

    response = agent.response("Extract capital structure from the memo.")
    print(response.content)
    print("---")
    print("template_data:", response.template_data)


if __name__ == "__main__":
    main()
