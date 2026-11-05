"""Fetch an author's works from the ORCID public API and merge them, add-only, into publications.json.

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


# --- Author-name normalization ------------------------------------------------
# Works imported into ORCID from some sources (e.g. Google Scholar/BibTeX) list
# contributors as "Family, Given" and end truncated lists with a literal
# "others". The site shows "Given Family", so names are rewritten here, both for
# fresh ORCID data and for names already in publications.json.

_PLACEHOLDER_AUTHORS = {"others", "et al", "et al."}
_NAME_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}


def normalize_author(name) -> str | None:
    """Return `name` as "Given Family", or None if it is not a real author.

    "Bhagwat, Sarang S" -> "Sarang S. Bhagwat": bare initials in the given
    names get a period, matching the rest of the list. Names already in display
    order only have their whitespace collapsed.
    """
    name = " ".join(str(name or "").split())
    if not name or name.casefold() in _PLACEHOLDER_AUTHORS:
        return None
    parts = [p.strip() for p in name.split(",")]
    if len(parts) == 2 and all(parts) and parts[1].casefold() not in _NAME_SUFFIXES:
        family, given = parts
        given = " ".join(f"{t}." if len(t) == 1 and t.isupper() else t for t in given.split())
        name = f"{given} {family}"
    return name


def normalize_authors(names) -> list[str]:
    """Normalize every name, drop placeholders and duplicates, keep order."""
    out: list[str] = []
    seen: set[str] = set()
    for n in names or []:
        n = normalize_author(n)
        if n and _norm_name(n) not in seen:
            seen.add(_norm_name(n))
            out.append(n)
    return out


def parse_contributors(work_detail: dict) -> list[str]:
    contributors = (work_detail.get("contributors") or {}).get("contributor", []) or []
    return normalize_authors((c.get("credit-name") or {}).get("value") for c in contributors)


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
        except Exception as err:
            print(f"warning: could not fetch authors for work {put_code}: {err}",
                  file=sys.stderr)
            pub["authors"] = []  # authors are best-effort
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "orcid_id": orcid_id,
        "publications": pubs,
    }


# --- Add-only merge ----------------------------------------------------------
# A sync may add publications and authors but never remove them: a flaky ORCID
# response (failed per-work detail fetch, empty /works list, a work hidden on
# ORCID) must not erase anything already on the site. Metadata such as title,
# venue, year and DOI still update from ORCID. To remove an entry on purpose,
# delete it from ORCID and then from data/publications.json by hand.

class ExistingFileError(ValueError):
    """The existing publications.json can't be read, so a merge can't be trusted."""


def _norm_name(name: str) -> str:
    return " ".join(str(name).split()).casefold()


def _norm_doi(doi) -> str | None:
    if not doi:
        return None
    d = str(doi).strip().lower()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", d)
    return d or None


def _norm_title(title) -> str | None:
    return _norm_name(title) if title else None


def merge_authors(existing: list[str], incoming: list[str]) -> list[str]:
    """Return an author list that contains every existing name.

    If ORCID's list already includes everyone we have, take it as-is (it may add
    authors or fix their order). Otherwise keep ours and append ORCID's extras.
    Both lists are normalized first, so "Family, Given" names already on the
    site match their "Given Family" form and "others" placeholders drop out.
    """
    existing = normalize_authors(existing)
    incoming = normalize_authors(incoming)
    incoming_norm = {_norm_name(n) for n in incoming}
    if all(_norm_name(n) in incoming_norm for n in existing):
        return incoming
    have = {_norm_name(n) for n in existing}
    return existing + [n for n in incoming if _norm_name(n) not in have]


def _find_match(pub: dict, existing: list[dict], used: set[int]) -> int | None:
    """Index of the existing entry that is the same work as `pub`, if any.

    Same DOI, or same ORCID put-code (e.g. a preprint moving from v1 to v2), or
    same title when neither has a DOI. Title-only matching is limited to
    DOI-less works so a preprint and its published version, which often share a
    title, are never folded into one entry.
    """
    doi, code, title = _norm_doi(pub.get("doi")), pub.get("put_code"), _norm_title(pub.get("title"))
    for test in (
        lambda e: doi is not None and _norm_doi(e.get("doi")) == doi,
        lambda e: code is not None and e.get("put_code") == code,
        lambda e: doi is None and _norm_doi(e.get("doi")) is None
                  and title is not None and _norm_title(e.get("title")) == title,
    ):
        for i, e in enumerate(existing):
            if i not in used and test(e):
                return i
    return None


def merge_publications(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Merge a fresh ORCID list into the existing one without dropping anything."""
    existing = list(existing or [])
    used: set[int] = set()
    merged: list[dict] = []
    for pub in incoming or []:
        i = _find_match(pub, existing, used)
        if i is None:
            merged.append(pub)
            continue
        used.add(i)
        merged.append({**existing[i], **pub,
                       "authors": merge_authors(existing[i].get("authors"), pub.get("authors"))})
    merged.extend({**e, "authors": normalize_authors(e.get("authors"))}
                  for i, e in enumerate(existing) if i not in used)
    merged.sort(key=lambda p: (p.get("year") is not None, p.get("year") or 0), reverse=True)
    return merged


def _read_existing_publications(out_path: pathlib.Path) -> list[dict]:
    if not out_path.exists():
        return []
    try:
        pubs = json.loads(out_path.read_text(encoding="utf-8"))["publications"]
    except Exception as err:
        raise ExistingFileError(f"cannot read {out_path}: {err}") from err
    if not isinstance(pubs, list):
        raise ExistingFileError(f"{out_path}: 'publications' is not a list")
    return pubs


def sync(orcid_id: str, out_path, *, opener=fetch_json) -> bool:
    """Fetch from ORCID, merge add-only into out_path, and write if anything changed."""
    out_path = pathlib.Path(out_path)
    existing = _read_existing_publications(out_path)  # before fetching: fail fast
    doc = build_publications(orcid_id, opener=opener)
    doc["publications"] = merge_publications(existing, doc["publications"])
    return write_publications_atomic(doc, out_path)


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
        changed = sync(orcid_id, out_path)
    except ExistingFileError as err:  # refuse to replace a file we can't merge into
        print(f"error: {err}; not writing publications.json", file=sys.stderr)
        return 1
    except Exception as err:  # fail-safe: never clobber the live list
        print(f"sync failed, keeping existing publications.json: {err}",
              file=sys.stderr)
        return 0

    count = len(json.loads(out_path.read_text(encoding="utf-8"))["publications"])
    print(f"{'updated' if changed else 'no change'}: {count} publications")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
