"""Fetch GitHub and PyPI metrics for the software listed in content.yml.

Writes data/software.json = {"repos": {slug: {stars, forks}},
"packages": {pkg: {last_month}}}, which js/main.js merges into the Software
cards. Mirrors sync_orcid.py: standard library only, network I/O injected via
an `opener` for testing, and fail-safe so a flaky API never clobbers the file.
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import re
import sys
import urllib.request

GITHUB_API = "https://api.github.com/repos"
PYPISTATS_API = "https://pypistats.org/api/packages"

REPO_RE = re.compile(r'^[ \t]*repo:[ \t]*["\']?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)',
                     re.MULTILINE)
PYPI_RE = re.compile(r'^[ \t]*pypi:[ \t]*["\']?([A-Za-z0-9_.-]+)',
                     re.MULTILINE)


def _dedupe(values: list[str]) -> list[str]:
    seen: set = set()
    out: list[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def extract_repos(content_text: str) -> list[str]:
    """Repo slugs ('owner/name') named on repo: lines, de-duplicated in order."""
    return _dedupe(REPO_RE.findall(content_text))


def extract_packages(content_text: str) -> list[str]:
    """PyPI package names named on pypi: lines, de-duplicated in order."""
    return _dedupe(PYPI_RE.findall(content_text))


def parse_repo_metrics(gh_json: dict) -> dict:
    return {
        "stars": int(gh_json.get("stargazers_count") or 0),
        "forks": int(gh_json.get("forks_count") or 0),
    }


def parse_package_downloads(stats_json: dict) -> int:
    return int((stats_json.get("data") or {}).get("last_month") or 0)


def fetch_json(url: str, timeout: int = 20, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "site-sync",
                                               **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_software(content_text: str, *, opener=fetch_json,
                   token: str | None = None) -> dict:
    gh_headers = {"Authorization": f"Bearer {token}"} if token else None
    repos: dict = {}
    for slug in extract_repos(content_text):
        try:
            gh = opener(f"{GITHUB_API}/{slug}", headers=gh_headers)
            repos[slug] = parse_repo_metrics(gh)
        except Exception as err:  # best-effort per entry
            print(f"warning: GitHub metrics failed for {slug}: {err}",
                  file=sys.stderr)
    packages: dict = {}
    for pkg in extract_packages(content_text):
        try:
            stats = opener(f"{PYPISTATS_API}/{pkg}/recent")
            packages[pkg] = {"last_month": parse_package_downloads(stats)}
        except Exception as err:
            print(f"warning: PyPI metrics failed for {pkg}: {err}",
                  file=sys.stderr)
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repos": repos,
        "packages": packages,
    }


def _comparable(doc: dict) -> str:
    return json.dumps({k: v for k, v in doc.items() if k != "generated_at"},
                      sort_keys=True)


def write_software_atomic(doc: dict, out_path) -> bool:
    out_path = pathlib.Path(out_path)
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            if _comparable(existing) == _comparable(doc):
                return False
        except Exception:
            pass
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    tmp.replace(out_path)
    return True


def main(argv=None) -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    content_path = root / "data" / "content.yml"
    out_path = root / "data" / "software.json"

    content_text = content_path.read_text(encoding="utf-8")
    token = os.environ.get("GITHUB_TOKEN") or None

    doc = build_software(content_text, token=token)

    # Fail-safe: if nothing came back but a populated file already exists, keep it.
    if not doc["repos"] and not doc["packages"] and out_path.exists():
        print("sync returned no metrics; keeping existing software.json",
              file=sys.stderr)
        return 0

    changed = write_software_atomic(doc, out_path)
    print(f"{'updated' if changed else 'no change'}: "
          f"{len(doc['repos'])} repos, {len(doc['packages'])} packages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
