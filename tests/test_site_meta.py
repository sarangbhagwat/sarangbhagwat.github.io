import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import site_meta  # noqa: E402


def test_read_meta_value_handles_quotes_and_comments():
    text = (
        'meta:\n'
        '  first_name: "Sarang"\n'
        "  last_name: 'Bhagwat'\n"
        "  title: Postdoctoral Researcher  # a comment\n"
    )
    assert site_meta.read_meta_value(text, "first_name") == "Sarang"
    assert site_meta.read_meta_value(text, "last_name") == "Bhagwat"
    assert site_meta.read_meta_value(text, "title") == "Postdoctoral Researcher"
    assert site_meta.read_meta_value(text, "middle_name") is None


def test_full_name_includes_middle_when_present():
    text = 'first_name: "Sarang"\nmiddle_name: "S."\nlast_name: "Bhagwat"\n'
    assert site_meta.full_name(text) == "Sarang S. Bhagwat"


def test_full_name_omits_absent_middle():
    text = 'first_name: "Ada"\nlast_name: "Lovelace"\n'
    assert site_meta.full_name(text) == "Ada Lovelace"


def test_full_name_none_when_last_name_missing():
    assert site_meta.full_name('first_name: "Ada"\n') is None
