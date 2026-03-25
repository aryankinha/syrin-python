"""Shared metadata serialization/deserialization for knowledge store backends."""

from __future__ import annotations

import json


def serialize_metadata_value(obj: object) -> object:
    """Convert a metadata value to JSON-serializable form.

    Lists are recursively serialized; primitives pass through; others become str.
    """
    if isinstance(obj, list):
        return [serialize_metadata_value(x) for x in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


def metadata_to_flat(
    metadata: dict[str, object],
) -> dict[str, str | int | float | bool]:
    """Flatten chunk metadata for backends that only accept scalar values (Chroma, Qdrant).

    Lists are JSON-encoded as strings; None values are skipped; other types become str.
    """
    out: dict[str, str | int | float | bool] = {}
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif isinstance(v, list):
            out[k] = json.dumps(v)
        else:
            out[k] = str(v)
    return out


def metadata_from_flat(
    raw: dict[str, object],
    skip_keys: set[str],
) -> dict[str, str | int | float | bool | None | list[str]]:
    """Reconstruct metadata from flat storage, reversing metadata_to_flat().

    JSON-encoded lists (strings starting with '[') are decoded back.
    Keys in skip_keys are excluded (e.g. 'document_id', 'chunk_index').
    """
    meta: dict[str, str | int | float | bool | None | list[str]] = {}
    for k, v in raw.items():
        if k in skip_keys:
            continue
        if isinstance(v, str) and v.startswith("["):
            try:
                meta[k] = json.loads(v)
            except json.JSONDecodeError:
                meta[k] = v
        elif isinstance(v, (str, int, float, bool, type(None))):
            meta[k] = v
    return meta
