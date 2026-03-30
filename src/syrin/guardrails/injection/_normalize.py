"""6.1: Input normalization pipeline for prompt injection defense.

Applied to all agent input paths: user input, tool output, knowledge retrieval, memory recall.

Steps:
1. NFKC Unicode normalization — collapses visually-identical lookalike chars
2. Control-char stripping — removes C0/C1 controls and Unicode direction overrides
3. Base64 decode-rescan — detects instructions hidden in base64-encoded payloads
4. URL-decode rescan — detects instructions hidden in percent-encoded strings
5. HTML-entity decode rescan — detects instructions hidden in HTML entities
"""

from __future__ import annotations

import base64
import html
import logging
import re
import unicodedata
import urllib.parse

_log = logging.getLogger(__name__)

# Control characters to strip: C0 controls (except \t, \n, \r), C1 controls, direction overrides
_CONTROL_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f"  # C0 controls except \t, \n, \r
    r"\x80-\x9f"  # C1 controls
    r"\u202a-\u202e\u2066-\u2069"  # Unicode bidi direction overrides
    r"]",
)

# Markers that suggest injection hidden in encoded payloads
_INJECTION_MARKERS = re.compile(
    r"ignore\s+(?:previous|all|above)|"
    r"disregard\s+(?:prior|previous|above|all)|"
    r"new\s+instruction|"
    r"system\s*(?:prompt|instruction)|"
    r"you\s+are\s+now|"
    r"forget\s+(?:all|everything|previous)",
    re.IGNORECASE,
)


def _strip_controls(text: str) -> str:
    """Strip control characters and direction overrides."""
    return _CONTROL_RE.sub("", text)


def _try_decode_base64(text: str) -> str | None:
    """Try to base64-decode text; return decoded string or None if not base64."""
    stripped = text.strip()
    # Rough base64 check: only base64 chars, length divisible by 4 after padding
    if not re.fullmatch(r"[A-Za-z0-9+/=\s]+", stripped):
        return None
    try:
        decoded = base64.b64decode(stripped + "==").decode("utf-8", errors="ignore")
        if decoded and decoded.isprintable() and len(decoded) > 5:
            return decoded
    except Exception:
        pass
    return None


def normalize_input(text: str, *, rescan_encoded: bool = True) -> str:
    """Normalize text through the prompt injection defense pipeline.

    Applies:
    1. NFKC Unicode normalization
    2. Control-character stripping (C0/C1 and direction overrides)
    3. Optional decode-rescan for base64, URL-encoding, HTML entities

    Args:
        text: Input text to normalize.
        rescan_encoded: If True, attempt to decode base64/URL/HTML and check for
            injections. Default: True. Disable for performance-critical paths where
            injection risk is low.

    Returns:
        Normalized text with control characters stripped.
    """
    if not text:
        return text

    # Step 1: NFKC normalization (collapses visually-identical lookalike chars)
    normalized = unicodedata.normalize("NFKC", text)

    # Step 2: Strip control characters and direction overrides
    normalized = _strip_controls(normalized)

    if rescan_encoded:
        # Step 3: URL-decode rescan
        try:
            url_decoded = urllib.parse.unquote(normalized)
            if url_decoded != normalized and _INJECTION_MARKERS.search(url_decoded):
                _log.warning(
                    "Possible injection detected in URL-encoded content; using normalized form."
                )
        except Exception:
            pass

        # Step 4: HTML entity decode rescan
        try:
            html_decoded = html.unescape(normalized)
            if html_decoded != normalized and _INJECTION_MARKERS.search(html_decoded):
                _log.warning(
                    "Possible injection detected in HTML-encoded content; using normalized form."
                )
        except Exception:
            pass

        # Step 5: Base64 decode rescan (only for short, likely-encoded segments)
        for segment in re.findall(r"\b[A-Za-z0-9+/]{20,}={0,2}\b", normalized):
            decoded = _try_decode_base64(segment)
            if decoded and _INJECTION_MARKERS.search(decoded):
                _log.warning(
                    "Possible injection detected in base64-encoded segment; segment left as-is."
                )
                break

    return normalized


__all__ = ["normalize_input"]
