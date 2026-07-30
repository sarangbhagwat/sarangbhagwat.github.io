"""Fetch an author's works from the ORCID public API and write publications.json.

Standard library only (urllib, json, re). No third-party dependencies.
"""
from __future__ import annotations

import json
import re


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
