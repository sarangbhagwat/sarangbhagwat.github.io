"""Fetch an author's works from the ORCID public API and write publications.json.

Standard library only (urllib, json, re). No third-party dependencies.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import re
import sys
import urllib.request


def read_orcid_id(content_yml_text: str) -> str:
    """Extract the orcid_id value from content.yml text without a YAML library."""
    m = re.search(r'^\s*orcid_id:\s*["\']?([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9X]{4})',
                  content_yml_text, re.MULTILINE)
    if not m:
        raise ValueError("orcid_id not found in content.yml")
    return m.group(1)


def extract_doi(external_ids: dict) -> tuple[str | None, str | None]:
    """Return (doi, url) from an ORCID external-ids block, or (None, None)."""
    for ext in (external_ids or {}).get("external-id", []) or []:
        if ext.get("external-id-type") == "doi":
            doi = ext.get("external-id-value")
            url = (ext.get("external-id-url") or {}).get("value")
            if doi and not url:
                url = f"https://doi.org/{doi}"
            return doi, url
    return None, None


def _year(summary: dict) -> int | None:
    pub_date = summary.get("publication-date") or {}
    year = (pub_date.get("year") or {}).get("value")
    return int(year) if year else None


def parse_work_summary(summary: dict) -> dict:
    """Map one ORCID work-summary to our publication dict (without authors)."""
    title = (((summary.get("title") or {}).get("title")) or {}).get("value")
    venue = (summary.get("journal-title") or {}).get("value")
    doi, url = extract_doi(summary.get("external-ids") or {})
    return {
        "title": title,
        "venue": venue,
        "year": _year(summary),
        "type": summary.get("type"),
        "doi": doi,
        "url": url,
        "put_code": summary.get("put-code"),
        "authors": [],
    }


def parse_works_summary_response(raw: dict) -> list[dict]:
    """Parse a full /works response into a de-duplicated, newest-first list."""
    seen: set = set()
    pubs: list[dict] = []
    for group in raw.get("group", []) or []:
        summaries = group.get("work-summary") or []
        if not summaries:
            continue
        pub = parse_work_summary(summaries[0])
        key = pub["doi"] or pub["title"]
        if key in seen:
            continue
        seen.add(key)
        pubs.append(pub)
    pubs.sort(key=lambda p: (p["year"] is not None, p["year"] or 0), reverse=True)
    return pubs


ORCID_API = "https://pub.orcid.org/v3.0"


def fetch_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_contributors(work_detail: dict) -> list[str]:
    contributors = (work_detail.get("contributors") or {}).get("contributor", []) or []
    names = []
    for c in contributors:
        name = (c.get("credit-name") or {}).get("value")
        if name:
            names.append(name)
    return names


def build_publications(orcid_id: str, *, opener=fetch_json) -> dict:
    raw = opener(f"{ORCID_API}/{orcid_id}/works")
    pubs = parse_works_summary_response(raw)
    for pub in pubs:
        put_code = pub.get("put_code")
        if not put_code:
            continue
        try:
            detail = opener(f"{ORCID_API}/{orcid_id}/work/{put_code}")
            pub["authors"] = parse_contributors(detail)
        except Exception:
            pub["authors"] = []  # authors are best-effort
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "orcid_id": orcid_id,
        "publications": pubs,
    }


def _comparable(doc: dict) -> str:
    return json.dumps({k: v for k, v in doc.items() if k != "generated_at"},
                      sort_keys=True)


def write_publications_atomic(doc: dict, out_path) -> bool:
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
    argv = list(sys.argv[1:] if argv is None else argv)
    root = pathlib.Path(__file__).resolve().parents[1]
    content_path = root / "data" / "content.yml"
    out_path = root / "data" / "publications.json"

    orcid_id = argv[0] if argv else read_orcid_id(
        content_path.read_text(encoding="utf-8"))

    try:
        doc = build_publications(orcid_id)
    except Exception as err:  # fail-safe: never clobber the live list
        print(f"sync failed, keeping existing publications.json: {err}",
              file=sys.stderr)
        return 0

    changed = write_publications_atomic(doc, out_path)
    print(f"{'updated' if changed else 'no change'}: "
          f"{len(doc['publications'])} publications")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
