import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import sync_head  # noqa: E402

CONTENT = (
    'meta:\n'
    '  first_name: "Sarang"\n'
    '  middle_name: "S."\n'
    '  last_name: "Bhagwat"\n'
    '  title: "Postdoctoral Researcher"\n'
    '  institution: "University of California, Berkeley"\n'
)

SAMPLE_HTML = (
    '<!doctype html>\n'
    '<html lang="en">\n'
    '<head>\n'
    '  <meta charset="utf-8" />\n'
    '  <title>Placeholder</title>\n'
    '  <meta name="description" content="Placeholder description." />\n'
    '  <script>var saved = "theme";</script>\n'
    '  <link rel="stylesheet" href="css/style.css" />\n'
    '</head>\n'
    '<body></body>\n'
    '</html>\n'
)


def test_build_title_is_the_full_name():
    assert sync_head.build_title(CONTENT) == "Sarang S. Bhagwat"


def test_build_description_names_role_and_institution():
    assert sync_head.build_description(CONTENT) == (
        "Personal website of Sarang S. Bhagwat, Postdoctoral Researcher, "
        "University of California, Berkeley."
    )


def test_build_description_falls_back_without_institution():
    text = 'first_name: "Ada"\nlast_name: "Lovelace"\ntitle: "Analyst"\n'
    assert sync_head.build_description(text) == (
        "Personal website of Ada Lovelace, Analyst."
    )


def test_build_description_is_bare_sentence_without_role_or_institution():
    text = 'first_name: "Ada"\nlast_name: "Lovelace"\n'
    assert sync_head.build_description(text) == "Personal website of Ada Lovelace."


def test_build_title_and_description_none_without_a_name():
    assert sync_head.build_title("meta:\n  title: X\n") is None
    assert sync_head.build_description("meta:\n  title: X\n") is None


def test_rewrite_head_replaces_both_tags():
    out = sync_head.rewrite_head(SAMPLE_HTML, "Ada Lovelace", "About Ada.")
    assert "<title>Ada Lovelace</title>" in out
    assert '<meta name="description" content="About Ada." />' in out
    assert "Placeholder" not in out


def test_rewrite_head_preserves_surrounding_markup():
    out = sync_head.rewrite_head(SAMPLE_HTML, "Ada Lovelace", "About Ada.")
    assert '<script>var saved = "theme";</script>' in out
    assert '<link rel="stylesheet" href="css/style.css" />' in out
    assert '<meta charset="utf-8" />' in out
    assert out.startswith("<!doctype html>\n")
    assert out.endswith("</html>\n")


def test_rewrite_head_preserves_crlf_line_endings():
    crlf_html = SAMPLE_HTML.replace("\n", "\r\n")
    out = sync_head.rewrite_head(crlf_html, "Ada Lovelace", "About Ada.")
    assert "\r\n" in out
    assert out.count("\r\n") == crlf_html.count("\r\n")
    assert "\n" not in out.replace("\r\n", "")


def test_rewrite_head_escapes_special_characters():
    out = sync_head.rewrite_head(SAMPLE_HTML, "Ada & Co", 'She said "hi".')
    assert "<title>Ada &amp; Co</title>" in out
    assert "&quot;hi&quot;" in out
    assert '<meta name="description" content="She said "hi"." />' not in out


def test_rewrite_head_raises_when_title_tag_absent():
    try:
        sync_head.rewrite_head("<html><head></head></html>", "A", "B")
    except ValueError:
        return
    raise AssertionError("expected ValueError when the title tag is absent")


def test_rewrite_head_raises_when_description_tag_absent():
    try:
        sync_head.rewrite_head("<html><head><title>x</title></head></html>", "A", "B")
    except ValueError:
        return
    raise AssertionError("expected ValueError when the description tag is absent")


def test_write_index_reports_change_then_no_change(tmp_path):
    out = tmp_path / "index.html"
    assert sync_head.write_index(SAMPLE_HTML, out) is True
    assert sync_head.write_index(SAMPLE_HTML, out) is False


def test_rewrite_head_is_idempotent():
    once = sync_head.rewrite_head(SAMPLE_HTML, "Ada Lovelace", "About Ada.")
    twice = sync_head.rewrite_head(once, "Ada Lovelace", "About Ada.")
    assert once == twice
