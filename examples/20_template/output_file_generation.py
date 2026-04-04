"""Output file generation — response.file, response.file_bytes, and citations.

- output_config=OutputFormat.TEXT | MARKDOWN | HTML | PDF | DOCX
- output_config=OutputConfig(citation_style=CitationStyle.FOOTNOTE, citation_include_page=True)
- response.file = Path to generated file
- response.file_bytes = raw bytes
- response.citations = parsed citations when citation_style is set
- save_as_pdf(), save_as_docx(), save_as() for manual saves
"""

from syrin import (
    Agent,
    CitationStyle,
    Model,
    OutputConfig,
    OutputFormat,
    save_as,
    save_as_docx,
    save_as_pdf,
)


def main() -> None:
    agent = Agent(
        model=Model.mock(
            response_mode="custom",
            custom_response="Capital structure: Authorized ₹50L, Issued ₹20L.",
            latency_min=0,
            latency_max=0,
        ),
        system_prompt="Return a short report.",
        output_config=OutputFormat.TEXT,
    )

    response = agent.run("Summarize capital structure.")
    print("Content:", response.content)
    print("File path:", response.file)
    print("File bytes length:", len(response.file_bytes) if response.file_bytes else 0)

    # With citations — parse and style [Source: doc.pdf, Page N] markers
    agent_cited = Agent(
        model=Model.mock(
            response_mode="custom",
            custom_response=(
                "Authorized capital is ₹50,00,000 [Source: moa.pdf, Page 3]. "
                "Face value per share is ₹10 [Source: moa.pdf, Page 4]."
            ),
            latency_min=0,
            latency_max=0,
        ),
        system_prompt="Return a report with citations.",
        output_config=OutputConfig(
            format=OutputFormat.TEXT,
            citation_style=CitationStyle.FOOTNOTE,
            citation_include_page=True,
        ),
    )
    r = agent_cited.run("Summarize capital.")
    print("Content with footnotes:", r.content)
    print("Citations:", [(c.source, c.page) for c in r.citations])

    # Manual save (markdown/text need no extra deps)
    save_as("Manual report", OutputFormat.MARKDOWN, "report.md", title="Report")
    try:
        save_as_pdf("PDF content", "report.pdf", title="PDF Report")
        print("Saved report.pdf (requires syrin[pdf-output])")
    except ImportError:
        print("Skip PDF: pip install syrin[pdf-output]")
    try:
        save_as_docx("DOCX content", "report.docx", title="DOCX Report")
        print("Saved report.docx (requires syrin[docx])")
    except ImportError:
        print("Skip DOCX: pip install syrin[docx]")


if __name__ == "__main__":
    main()
