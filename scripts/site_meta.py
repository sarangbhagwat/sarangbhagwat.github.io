"""Read the flat scalar fields of the `meta:` block in data/content.yml.

Shared by the generator scripts so the name has one reader rather than one per
script. Standard library only — a regex reader keeps the scripts runnable in CI
with a bare Python install, no YAML dependency.
"""
from __future__ import annotations

import re


def meta_block(content_text: str) -> str:
    """The lines of the top-level `meta:` block, or the whole text without one.

    The block ends at the next line that starts in column 0 with something
    other than a comment (the next top-level key).
    """
    m = re.search(r"^meta:[ \t]*(?:#.*)?$", content_text, re.MULTILINE)
    if not m:
        return content_text
    rest = content_text[m.end():]
    end = re.search(r"^[^\s#]", rest, re.MULTILINE)
    return rest[:end.start()] if end else rest


def read_meta_value(content_text: str, key: str) -> str | None:
    """Extract a scalar meta value (e.g. first_name) from content.yml text.

    Handles double-quoted, single-quoted, and bare values with optional inline
    comments — enough for the flat name fields, without a YAML dependency.
    When the text has a top-level `meta:` block, only that block is searched,
    so a missing meta key can't be filled by a same-named key elsewhere (e.g.
    a talk's `title:`).
    """
    content_text = meta_block(content_text)
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
