import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import sync_orcid  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_read_orcid_id_extracts_quoted_value():
    text = 'meta:\n  name: "X"\n  orcid_id: "0000-0002-1825-0097"\n'
    assert sync_orcid.read_orcid_id(text) == "0000-0002-1825-0097"


def test_read_orcid_id_missing_raises():
    try:
        sync_orcid.read_orcid_id("meta:\n  name: X\n")
    except ValueError:
        return
    raise AssertionError("expected ValueError when orcid_id absent")


def test_extract_doi_returns_value_and_url():
    ext = {
        "external-id": [
            {
                "external-id-type": "doi",
                "external-id-value": "10.1000/abc123",
                "external-id-url": {"value": "https://doi.org/10.1000/abc123"},
            }
        ]
    }
    assert sync_orcid.extract_doi(ext) == ("10.1000/abc123", "https://doi.org/10.1000/abc123")


def test_extract_doi_none_when_absent():
    assert sync_orcid.extract_doi({"external-id": []}) == (None, None)


def test_parse_work_summary_maps_fields():
    summary = load_fixture("orcid_works_summary.json")["group"][0]["work-summary"][0]
    pub = sync_orcid.parse_work_summary(summary)
    assert pub["title"] == "Catalytic conversion of biomass"
    assert pub["venue"] == "Nature Catalysis"
    assert pub["year"] == 2023
    assert pub["type"] == "journal-article"
    assert pub["doi"] == "10.1000/abc123"
    assert pub["url"] == "https://doi.org/10.1000/abc123"
    assert pub["put_code"] == 111


def test_parse_response_sorts_newest_first_and_handles_missing():
    raw = load_fixture("orcid_works_summary.json")
    pubs = sync_orcid.parse_works_summary_response(raw)
    assert [p["put_code"] for p in pubs][:2] == [111, 222]  # 2023 before 2021
    no_date = [p for p in pubs if p["put_code"] == 333][0]
    assert no_date["year"] is None
    assert no_date["venue"] is None


def test_parse_response_deduplicates_same_doi_across_groups():
    raw = {
        "group": [
            {
                "work-summary": [
                    {
                        "put-code": 111,
                        "title": {"title": {"value": "Catalytic conversion of biomass"}},
                        "journal-title": {"value": "Nature Catalysis"},
                        "publication-date": {"year": {"value": "2023"}},
                        "type": "journal-article",
                        "external-ids": {
                            "external-id": [
                                {
                                    "external-id-type": "doi",
                                    "external-id-value": "10.1000/abc123",
                                    "external-id-url": {"value": "https://doi.org/10.1000/abc123"},
                                }
                            ]
                        },
                    }
                ]
            },
            {
                "work-summary": [
                    {
                        "put-code": 999,
                        "title": {"title": {"value": "Catalytic conversion of biomass (duplicate record)"}},
                        "journal-title": {"value": "Nature Catalysis"},
                        "publication-date": {"year": {"value": "2023"}},
                        "type": "journal-article",
                        "external-ids": {
                            "external-id": [
                                {
                                    "external-id-type": "doi",
                                    "external-id-value": "10.1000/abc123",
                                    "external-id-url": {"value": "https://doi.org/10.1000/abc123"},
                                }
                            ]
                        },
                    }
                ]
            },
        ]
    }
    pubs = sync_orcid.parse_works_summary_response(raw)
    assert len(pubs) == 1
    assert pubs[0]["put_code"] == 111  # first occurrence wins


def test_parse_response_uses_first_work_summary_in_group():
    raw = {
        "group": [
            {
                "work-summary": [
                    {
                        "put-code": 111,
                        "title": {"title": {"value": "Preferred title"}},
                        "journal-title": {"value": "Nature Catalysis"},
                        "publication-date": {"year": {"value": "2023"}},
                        "type": "journal-article",
                        "external-ids": {"external-id": []},
                    },
                    {
                        "put-code": 222,
                        "title": {"title": {"value": "Alternate title"}},
                        "journal-title": {"value": "Alt Journal"},
                        "publication-date": {"year": {"value": "2022"}},
                        "type": "journal-article",
                        "external-ids": {"external-id": []},
                    },
                ]
            }
        ]
    }
    pubs = sync_orcid.parse_works_summary_response(raw)
    assert len(pubs) == 1
    assert pubs[0]["put_code"] == 111
    assert pubs[0]["title"] == "Preferred title"


def test_parse_contributors_reads_credit_names():
    detail = load_fixture("orcid_work_detail.json")
    assert sync_orcid.parse_contributors(detail) == ["Your Name", "Coauthor One", "Coauthor Two"]


def test_parse_contributors_empty_when_absent():
    assert sync_orcid.parse_contributors({}) == []


def test_build_publications_assembles_document():
    works = load_fixture("orcid_works_summary.json")
    detail = load_fixture("orcid_work_detail.json")

    def fake_opener(url, timeout=20):
        if url.endswith("/works"):
            return works
        return detail  # any per-work detail request

    doc = sync_orcid.build_publications("0000-0002-1825-0097", opener=fake_opener)
    assert doc["orcid_id"] == "0000-0002-1825-0097"
    assert "generated_at" in doc
    assert doc["publications"][0]["put_code"] == 111
    assert doc["publications"][0]["authors"][0] == "Your Name"


def test_write_publications_atomic_only_writes_on_change(tmp_path):
    out = tmp_path / "publications.json"
    doc = {"orcid_id": "x", "publications": [], "generated_at": "t"}
    assert sync_orcid.write_publications_atomic(doc, out) is True
    # Second identical write (ignoring generated_at) should be a no-op.
    doc2 = {"orcid_id": "x", "publications": [], "generated_at": "different-time"}
    assert sync_orcid.write_publications_atomic(doc2, out) is False


# --- Add-only merge: syncs may add authors/publications, never remove them ---

def _pub(put_code, doi, title="T", year=2024, authors=None, **extra):
    return {"title": title, "venue": "V", "year": year, "type": "journal-article",
            "doi": doi, "url": f"https://doi.org/{doi}" if doi else None,
            "put_code": put_code, "authors": list(authors or []), **extra}


def test_merge_authors_keeps_names_missing_from_incoming():
    assert sync_orcid.merge_authors(["A", "B", "C"], ["A", "C"]) == ["A", "B", "C"]


def test_merge_authors_keeps_existing_when_fetch_failed():
    assert sync_orcid.merge_authors(["A", "B"], []) == ["A", "B"]


def test_merge_authors_adopts_incoming_order_when_it_has_everyone():
    assert sync_orcid.merge_authors(["A", "C"], ["A", "B", "C"]) == ["A", "B", "C"]


def test_merge_authors_appends_new_names_when_some_are_missing():
    assert sync_orcid.merge_authors(["A", "B"], ["A", "D"]) == ["A", "B", "D"]


def test_merge_authors_matches_names_ignoring_case_and_spacing():
    assert sync_orcid.merge_authors(["Jeremy  Guest"], ["jeremy guest", "X"]) == ["jeremy guest", "X"]


def test_merge_publications_keeps_publication_missing_from_incoming():
    existing = [_pub(1, "10.1/a", year=2025, authors=["A"]), _pub(2, "10.1/b", year=2024, authors=["B"])]
    incoming = [_pub(1, "10.1/a", year=2025, authors=["A"])]
    merged = sync_orcid.merge_publications(existing, incoming)
    assert [p["put_code"] for p in merged] == [1, 2]
    assert merged[1]["authors"] == ["B"]


def test_merge_publications_empty_incoming_keeps_everything():
    existing = [_pub(1, "10.1/a", authors=["A"]), _pub(2, "10.1/b", authors=["B"])]
    assert sync_orcid.merge_publications(existing, []) == existing


def test_merge_publications_adds_new_publication_newest_first():
    existing = [_pub(1, "10.1/a", year=2024)]
    incoming = [_pub(1, "10.1/a", year=2024), _pub(9, "10.1/new", year=2026)]
    merged = sync_orcid.merge_publications(existing, incoming)
    assert [p["put_code"] for p in merged] == [9, 1]


def test_merge_publications_matches_doi_across_url_and_case_forms():
    existing = [_pub(1, "https://doi.org/10.1/ABC", authors=["A", "B"])]
    incoming = [_pub(5, "10.1/abc", title="Updated title", authors=["A"])]
    merged = sync_orcid.merge_publications(existing, incoming)
    assert len(merged) == 1
    assert merged[0]["title"] == "Updated title"      # metadata may update
    assert merged[0]["authors"] == ["A", "B"]         # authors never shrink


def test_merge_publications_matches_put_code_when_doi_changes():
    existing = [_pub(1, "10.1/preprint/v1", authors=["A"])]
    incoming = [_pub(1, "10.1/preprint/v2", authors=["A"])]
    merged = sync_orcid.merge_publications(existing, incoming)
    assert len(merged) == 1
    assert merged[0]["doi"] == "10.1/preprint/v2"


def test_merge_publications_unchanged_input_is_identity():
    existing = [_pub(1, "10.1/a", year=2025, authors=["A"]), _pub(2, None, title="No DOI", year=None)]
    assert sync_orcid.merge_publications(existing, [dict(p) for p in existing]) == existing


def _write_existing(path, pubs):
    path.write_text(json.dumps({"generated_at": "t", "orcid_id": "x", "publications": pubs}),
                    encoding="utf-8")


def test_sync_failed_author_fetch_and_missing_work_lose_nothing(tmp_path):
    out = tmp_path / "publications.json"
    _write_existing(out, [_pub(111, "10.1000/abc123", year=2023, authors=["Your Name", "Coauthor One"]),
                          _pub(777, "10.1/gone", year=2020, authors=["Someone"])])
    works = load_fixture("orcid_works_summary.json")

    def flaky_opener(url, timeout=20):
        if url.endswith("/works"):
            return works
        raise OSError("503 Service Unavailable")

    sync_orcid.sync("x", out, opener=flaky_opener)
    pubs = {p["put_code"]: p for p in json.loads(out.read_text(encoding="utf-8"))["publications"]}
    assert pubs[111]["authors"] == ["Your Name", "Coauthor One"]
    assert pubs[777]["authors"] == ["Someone"]
    assert {222, 333} <= set(pubs)   # new works from ORCID were still added


def test_sync_empty_orcid_response_keeps_existing_list(tmp_path):
    out = tmp_path / "publications.json"
    existing = [_pub(1, "10.1/a", authors=["A"])]
    _write_existing(out, existing)
    changed = sync_orcid.sync("x", out, opener=lambda url, timeout=20: {"group": []})
    assert changed is False
    assert json.loads(out.read_text(encoding="utf-8"))["publications"] == existing


def test_sync_refuses_to_overwrite_unreadable_existing_file(tmp_path):
    out = tmp_path / "publications.json"
    out.write_text("{not json", encoding="utf-8")
    works = load_fixture("orcid_works_summary.json")
    try:
        sync_orcid.sync("x", out, opener=lambda url, timeout=20: works if url.endswith("/works") else {})
    except ValueError:
        assert out.read_text(encoding="utf-8") == "{not json"
        return
    raise AssertionError("expected ValueError for an unreadable existing file")


def test_sync_creates_file_when_none_exists(tmp_path):
    out = tmp_path / "publications.json"
    works = load_fixture("orcid_works_summary.json")
    detail = load_fixture("orcid_work_detail.json")
    assert sync_orcid.sync("x", out, opener=lambda url, timeout=20: works if url.endswith("/works") else detail) is True
    assert len(json.loads(out.read_text(encoding="utf-8"))["publications"]) == 3
