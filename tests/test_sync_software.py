import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import sync_software  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


CONTENT = """meta:
  first_name: "A"
software:
  - name: "Tool One"
    repo: "octo/example"
    pypi: "example"
  - name: "Tool Two"
    repo: "org/second-tool"
  - name: "Dup"
    repo: "octo/example"
"""


def test_extract_repos_dedupes_in_order():
    assert sync_software.extract_repos(CONTENT) == ["octo/example", "org/second-tool"]


def test_extract_packages_reads_pypi_lines():
    assert sync_software.extract_packages(CONTENT) == ["example"]


def test_extract_repos_empty_when_none():
    assert sync_software.extract_repos("meta:\n  first_name: X\n") == []


def test_parse_repo_metrics_maps_fields():
    gh = load_fixture("github_repo.json")
    assert sync_software.parse_repo_metrics(gh) == {"stars": 128, "forks": 17}


def test_parse_package_downloads_reads_last_month():
    stats = load_fixture("pypistats_recent.json")
    assert sync_software.parse_package_downloads(stats) == 1234


def test_build_software_assembles_document():
    gh = load_fixture("github_repo.json")
    stats = load_fixture("pypistats_recent.json")

    def fake_opener(url, timeout=20, headers=None):
        if "api.github.com" in url:
            return gh
        return stats

    doc = sync_software.build_software(CONTENT, opener=fake_opener)
    assert "generated_at" in doc
    assert doc["repos"]["octo/example"] == {"stars": 128, "forks": 17}
    assert doc["repos"]["org/second-tool"] == {"stars": 128, "forks": 17}
    assert doc["packages"]["example"] == {"last_month": 1234}


def test_build_software_survives_fetch_failure():
    def flaky_opener(url, timeout=20, headers=None):
        raise RuntimeError("network down")

    doc = sync_software.build_software(CONTENT, opener=flaky_opener)
    # An entry that failed is simply absent; the doc is still well-formed.
    assert doc["repos"] == {}
    assert doc["packages"] == {}


def test_write_software_atomic_only_writes_on_change(tmp_path):
    out = tmp_path / "software.json"
    doc = {"repos": {}, "packages": {}, "generated_at": "t"}
    assert sync_software.write_software_atomic(doc, out) is True
    doc2 = {"repos": {}, "packages": {}, "generated_at": "different-time"}
    assert sync_software.write_software_atomic(doc2, out) is False
