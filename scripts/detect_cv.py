"""Detect the CV file in assets/ by a prefix derived from the name in content.yml.

The prefix is "<last>-<first>_CV", built from the first_name/last_name fields in
data/content.yml, so nothing here is tied to a specific person. Writes
data/cv.json = {"file": "assets/<name>.pdf"} for the site to read, letting the
CV be renamed (e.g. with a date suffix) without touching any code. Standard
library only; runs locally or in CI whenever assets/ or content.yml changes.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ASSETS_DIRNAME = "assets"


def read_name_part(content_text: str, key: str) -> str | None:
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


def cv_prefix(first: str, last: str) -> str:
    """Build the CV filename prefix ('<last>-<first>_CV') from name parts."""
    return f"{last.strip()}-{first.strip()}_CV"


def find_cv(assets_dir: pathlib.Path, prefix: str) -> str | None:
    """Return the CV filename (not path) matching the prefix, or None.

    When several match, the lexicographically greatest name wins, so a dated or
    versioned suffix (e.g. Bhagwat-Sarang_CV_2026-07.pdf) is preferred over an
    older one. Naming new files so they sort after the previous one keeps the
    newest CV live.
    """
    matches = sorted(
        p.name for p in assets_dir.glob(f"{prefix}*.pdf") if p.is_file()
    )
    return matches[-1] if matches else None


def render_cv_json(cv_name: str | None) -> str:
    """Serialize the cv.json document for a detected filename (or None)."""
    file = f"{ASSETS_DIRNAME}/{cv_name}" if cv_name else None
    return json.dumps({"file": file}, indent=2) + "\n"


def write_cv_json(cv_name: str | None, out_path: pathlib.Path) -> bool:
    """Write cv.json, returning True only if the content changed."""
    new_text = render_cv_json(cv_name)
    if out_path.exists() and out_path.read_text(encoding="utf-8") == new_text:
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(new_text, encoding="utf-8")
    return True


def main(argv=None) -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    content_path = root / "data" / "content.yml"
    assets_dir = root / ASSETS_DIRNAME
    out_path = root / "data" / "cv.json"

    text = content_path.read_text(encoding="utf-8")
    first = read_name_part(text, "first_name")
    last = read_name_part(text, "last_name")

    if not (first and last):
        print("warning: first_name/last_name missing in content.yml; cannot detect CV",
              file=sys.stderr)
        cv_name = None
    else:
        prefix = cv_prefix(first, last)
        cv_name = find_cv(assets_dir, prefix)
        if cv_name is None:
            print(f"warning: no CV matching '{prefix}*.pdf' in {assets_dir}",
                  file=sys.stderr)

    changed = write_cv_json(cv_name, out_path)
    print(f"{'updated' if changed else 'no change'}: cv = {cv_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
