"""PDF text extraction and sending to agent.

Use pdf_extract_text() to get text from PDF bytes, then send that text to the
agent. Requires optional dependency: pip install syrin[pdf] (docling).
Without it, the example shows the ImportError and suggests installation.

Run:
    python -m examples.18_multimodal.pdf_extract_example

Covers: pdf_extract_text, file_to_message (for contrast), optional dependency.
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from syrin import Agent, Model
from syrin.multimodal import file_to_message


def main() -> None:
    # Minimal PDF bytes (valid PDF with one empty page) for demo
    # In real use you would do: Path("document.pdf").read_bytes()
    minimal_pdf = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000052 00000 n
0000000101 00000 n
trailer << /Size 4 /Root 1 0 R >>
startxref
178
%%EOF"""

    # Option 1: Send PDF as file (data URL) — agent would need to support it or you use vision
    data_url = file_to_message(minimal_pdf, "application/pdf")
    print("file_to_message( pdf_bytes, 'application/pdf' ) -> data URL length:", len(data_url))

    # Option 2: Extract text and send as text (requires syrin[pdf])
    try:
        from syrin.multimodal import pdf_extract_text

        text = pdf_extract_text(minimal_pdf)
        print("pdf_extract_text( pdf_bytes ) -> length:", len(text))
        print("  (minimal PDF may yield empty or little text)")

        agent = Agent(
            model=Model.Almock(latency_min=0, latency_max=0),
            system_prompt="You summarize documents.",
        )
        if text.strip():
            r = agent.response(f"Summarize this document:\n\n{text}")
            print("Agent response (summary):", (r.content or "")[:200])
        else:
            r = agent.response("I have a PDF with no extractable text. Say 'No text'.")
            print("Agent response:", (r.content or "")[:200])
    except ImportError as e:
        print("pdf_extract_text requires docling. Install with: pip install syrin[pdf]")
        print("  Error:", e)


if __name__ == "__main__":
    main()
