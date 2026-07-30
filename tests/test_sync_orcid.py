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
