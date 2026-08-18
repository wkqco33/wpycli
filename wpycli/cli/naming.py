from __future__ import annotations

import keyword

from wpycli import UsageError


def normalize_identifier(
    value: str,
    *,
    label: str,
    reserved: frozenset[str] = frozenset(),
) -> str:
    """Normalize a CLI name and ensure it is safe as a Python identifier."""
    normalized = value.lower().replace("-", "_")
    if (
        not normalized
        or not normalized.isidentifier()
        or keyword.iskeyword(normalized)
        or normalized in reserved
    ):
        raise UsageError(
            f"invalid {label} {value!r}; use a Python identifier with optional hyphens"
        )
    return normalized
