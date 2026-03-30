"""Structured logging for Syrin — JSON lines for production, human-readable for dev.

Example::

    import logging
    from syrin.logging import SyrinHandler, LogFormat

    # Production: JSON to stdout for log aggregators
    logging.getLogger("syrin").addHandler(SyrinHandler(format=LogFormat.JSON))

    # Development: human-readable
    logging.getLogger("syrin").addHandler(SyrinHandler(format=LogFormat.TEXT))
"""

from syrin.logging._handler import LogFormat, SyrinHandler

__all__ = ["LogFormat", "SyrinHandler"]
