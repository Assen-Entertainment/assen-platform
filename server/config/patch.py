"""Shared helper for PATCH (partial-update) endpoints.

A Ninja partial-update schema leaves every unsent field as ``None``, so the
handlers grew the same ``if payload.x is not None: obj.x = payload.x`` chain over
and over. :func:`apply_optional` collapses that chain for the common case where the
model attribute and the payload field share a name.
"""

from __future__ import annotations

from collections.abc import Iterable


def apply_optional(obj: object, payload: object, fields: Iterable[str]) -> list[str]:
    """Copy each of ``fields`` from ``payload`` onto ``obj`` when it is not ``None``.

    Only the fields the client actually sent (non-``None`` on the partial-update
    schema) are written, so an omitted field keeps the stored value. This handles
    the 1:1 case where ``obj`` and ``payload`` share the field name; a field whose
    model attribute differs from the payload name, that needs validation, or where
    ``None`` is itself a meaningful value (a nullable column) must stay inline.

    Returns the names actually changed, so a caller may narrow its write with
    ``obj.save(update_fields=apply_optional(...))`` when nothing else changed.
    """
    changed: list[str] = []
    for field in fields:
        value = getattr(payload, field)
        if value is not None:
            setattr(obj, field, value)
            changed.append(field)
    return changed
