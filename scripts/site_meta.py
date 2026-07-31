"""Read the flat scalar fields of the `meta:` block in data/content.yml.

Shared by the generator scripts so the name has one reader rather than one per
script. Standard library only — a regex reader keeps the scripts runnable in CI
with a bare Python install, no YAML dependency.
"""
from __future__ import annotations

import re


def read_meta_value(content_text: str, key: str) -> str | None:
    """Extract a scalar meta value (e.g. first_name) from content.yml text.

    Handles double-quoted, single-quoted, and bare values with optional inline
    comments — enough for the flat name fields, without a YAML dependency.
    """
    k = re.escape(key)
    for pat in (rf'^[ \t]*{k}:[ \t]*"([^"]*)"',
                rf"^[ \t]*{k}:[ \t]*'([^']*)'",
                rf'^[ \t]*{k}:[ \t]*([^"\'#\n][^#\n]*?)[ \t]*(?:#.*)?$'):
        m = re.search(pat, content_text, re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def full_name(content_text: str) -> str | None:
    """Assemble "first middle last", or None when first or last is missing.

    Middle is optional and used as written — a full name or an initial ("S.").
    Mirrors fullName() in js/main.js.
    """
    first = read_meta_value(content_text, "first_name")
    last = read_meta_value(content_text, "last_name")
    if not (first and last):
        return None
    middle = read_meta_value(content_text, "middle_name")
    return " ".join(part for part in (first, middle, last) if part)
