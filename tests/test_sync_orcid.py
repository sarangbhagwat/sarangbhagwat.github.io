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
