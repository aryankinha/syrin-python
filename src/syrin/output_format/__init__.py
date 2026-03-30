"""Public output-format package facade.

This package exposes output-formatting models and file-export helpers used for
structured, citeable, or downloadable agent output. Import from
``syrin.output_format`` for output config types, formatters, citation helpers,
and file writers.
"""

from syrin.output_format._core import (
    Citation,
    CitationStyle,
    OutputConfig,
    OutputFormat,
    OutputFormatter,
    apply_citation_to_content,
    format_to_file,
    get_formatter,
    save_as,
    save_as_docx,
    save_as_pdf,
)

__all__ = [
    "Citation",
    "CitationStyle",
    "OutputFormat",
    "OutputConfig",
    "OutputFormatter",
    "apply_citation_to_content",
    "format_to_file",
    "get_formatter",
    "save_as_pdf",
    "save_as_docx",
    "save_as",
]
