"""Detect the CV file in assets/ by its 'Bhagwat-Sarang_CV' prefix.

Writes data/cv.json = {"file": "assets/<name>.pdf"} for the site to read, so the
CV can be renamed (e.g. with a date suffix) without touching any code. Standard
library only; runs locally or in CI whenever assets/ changes.
"""
from __future__ import annotations

import json
import pathlib
import sys

CV_PREFIX = "Bhagwat-Sarang_CV"
ASSETS_DIRNAME = "assets"


def find_cv(assets_dir: pathlib.Path) -> str | None:
    """Return the CV filename (not path) matching the prefix, or None.

    When several match, the lexicographically greatest name wins, so a dated or
    versioned suffix (e.g. Bhagwat-Sarang_CV_2026-07.pdf) is preferred over an
    older one. Naming new files so they sort after the previous one keeps the
    newest CV live.
    """
    matches = sorted(
        p.name for p in assets_dir.glob(f"{CV_PREFIX}*.pdf") if p.is_file()
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
    assets_dir = root / ASSETS_DIRNAME
    out_path = root / "data" / "cv.json"

    cv_name = find_cv(assets_dir)
    if cv_name is None:
        print(f"warning: no CV matching '{CV_PREFIX}*.pdf' in {assets_dir}",
              file=sys.stderr)
    changed = write_cv_json(cv_name, out_path)
    print(f"{'updated' if changed else 'no change'}: cv = {cv_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
