"""Rewrite the <title> and meta description in index.html from content.yml.

The name, role, and institution live in data/content.yml like everything else
the site shows. Rewriting them into the static head keeps crawlers and no-JS
visitors seeing the same thing the page renders. Standard library only; runs
locally or in CI whenever content.yml changes.
"""
from __future__ import annotations

import html
import pathlib
import re
import sys

from site_meta import full_name, read_meta_value

TITLE_RE = re.compile(r"(<title>)(.*?)(</title>)", re.DOTALL)
DESCRIPTION_RE = re.compile(
    r'(<meta\s+name="description"\s+content=")(.*?)(")', re.DOTALL
)


def build_title(content_text: str) -> str | None:
    """The page title: the full display name, or None if it can't be built."""
    return full_name(content_text)


def build_description(content_text: str) -> str | None:
    """One sentence describing the site owner, or None without a name.

    Role and institution are appended the same way the hero subtitle joins them
    in js/main.js. Both are optional, and the sentence simply stops early when
    they are absent. Deliberately no "at the" before the institution: the right
    article depends on the name ("at the University of X" but "at Stanford
    University"), and this file cannot know which applies.
    """
    name = full_name(content_text)
    if not name:
        return None
    affiliation = ", ".join(
        part for part in (read_meta_value(content_text, "title"),
                          read_meta_value(content_text, "institution")) if part
    )
    if affiliation:
        return f"Personal website of {name}, {affiliation}."
    return f"Personal website of {name}."


def _replace_one(pattern: re.Pattern, value: str, text: str, label: str) -> str:
    """Substitute the single tag `pattern` matches, escaping `value` first.

    A lambda supplies the replacement so backslashes and group references in a
    name can't be interpreted as substitution syntax.
    """
    escaped = html.escape(value, quote=True)
    new_text, count = pattern.subn(
        lambda m: m.group(1) + escaped + m.group(3), text, count=1
    )
    if count == 0:
        raise ValueError(f"no {label} tag found in index.html")
    return new_text


def rewrite_head(html_text: str, title: str, description: str) -> str:
    """Return index.html with the title and description tag contents replaced."""
    out = _replace_one(TITLE_RE, title, html_text, "<title>")
    return _replace_one(DESCRIPTION_RE, description, out, 'meta name="description"')


def read_html(path: pathlib.Path) -> str:
    """Read a file preserving its line endings verbatim (no translation)."""
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write_index(new_html: str, out_path: pathlib.Path) -> bool:
    """Write index.html verbatim, returning True only if the content changed."""
    if out_path.exists() and read_html(out_path) == new_html:
        return False
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(new_html)
    return True


def main(argv=None) -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    content_path = root / "data" / "content.yml"
    index_path = root / "index.html"

    text = content_path.read_text(encoding="utf-8")
    title = build_title(text)
    description = build_description(text)

    if not (title and description):
        print("warning: first_name/last_name missing in content.yml; "
              "leaving index.html unchanged", file=sys.stderr)
        return 0

    try:
        new_html = rewrite_head(read_html(index_path), title, description)
    except ValueError as err:  # fail-safe: never mangle a live page
        print(f"warning: {err}; leaving index.html unchanged", file=sys.stderr)
        return 0

    changed = write_index(new_html, index_path)
    print(f"{'updated' if changed else 'no change'}: title = {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
