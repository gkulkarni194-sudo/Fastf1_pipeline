from __future__ import annotations

import re


def slug(value: str) -> str:
    """Convert a string to a URL/path-safe slug.

    Examples:
        >>> slug("Bahrain Grand Prix")
        'bahrain_grand_prix'
        >>> slug("Q")
        'q'
    """
    result = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    if not result:
        raise ValueError("Path component cannot be empty.")
    return result
