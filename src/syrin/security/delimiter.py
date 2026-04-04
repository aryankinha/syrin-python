"""DelimiterFactory — creates unpredictable delimiters with random salt."""

from __future__ import annotations

import secrets


class DelimiterFactory:
    """Creates unpredictable delimiters with random salt.

    Delimiters are used to wrap prompt sections to reduce predictability of
    prompt injection attacks. Each call produces a unique delimiter.

    Example:
        >>> d1 = DelimiterFactory.make()
        >>> d2 = DelimiterFactory.make()
        >>> assert d1 != d2
        >>> assert d1.startswith("##")
    """

    @staticmethod
    def make(prefix: str = "##") -> str:
        """Generate a delimiter with random salt component.

        Args:
            prefix: Prefix string to prepend. Defaults to ``"##"``.

        Returns:
            A delimiter string of the form ``{prefix}{random_hex}``.
        """
        return f"{prefix}{secrets.token_hex(8)}"
