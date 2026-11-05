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


# --- Static content: regions, links, structured data ------------------------

import json  # noqa: E402

FULL_CONTENT = CONTENT + (
    '  tagline: "Builds **tools** for [BioSTEAM](https://biosteam.org) & more."\n'
    '  email: "ada@example.org"\n'
    '  scholar_url: "https://scholar.example/ada?x=1&y=2"\n'
    '  links:\n'
    '    - { label: "ada@example.org", url: "mailto:ada@example.org" }\n'
    '    - { label: "GitHub", url: "https://github.com/ada" }\n'
    'about:\n'
    '  - "Not a link item."\n'
    'education:\n'
    '  - { degree: "Ph.D.", institution: "Uni A", year: "2025" }\n'
    '  - { degree: "M.S.", institution: "Uni B", year: "2019" }\n'
)

PAGE_HTML = (
    '<head>\n'
    '  <title>x</title>\n'
    '  <meta name="description" content="x" />\n'
    '  <!-- generated:head (do not edit) -->\n'
    '  <!-- /generated:head -->\n'
    '</head>\n'
    '<a class="nav-name" href="#hero">Your Name</a>\n'
    '    <!-- generated:hero (do not edit) -->\n'
    '    <h1 id="hero-name"></h1>\n'
    '    <!-- /generated:hero -->\n'
    '<ul id="education-list">\n'
    '  <!-- generated:education (do not edit) -->\n'
    '  <!-- /generated:education -->\n'
    '</ul>\n'
    '<a id="scholar-link" href="#">See all</a>\n'
    '<span id="footer-year"></span> <span id="footer-name"></span>\n'
)


def _site(tmp_path, cv=True):
    (tmp_path / "CNAME").write_text("ada.example\n", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "cv.json").write_text(
        json.dumps({"file": "assets/Lovelace-Ada_CV.pdf" if cv else None}), encoding="utf-8")
    return tmp_path


def test_read_flow_list_reads_nested_and_top_level_lists():
    links = sync_head.read_flow_list(FULL_CONTENT, "links")
    assert [l["label"] for l in links] == ["ada@example.org", "GitHub"]
    edu = sync_head.read_flow_list(FULL_CONTENT, "education")
    assert [e["institution"] for e in edu] == ["Uni A", "Uni B"]
    assert sync_head.read_flow_list(FULL_CONTENT, "missing") == []


def test_rich_text_mirrors_main_js_and_escapes():
    out = sync_head.rich_text('Use **bold**, *it* and [a & b](https://x.org/?q=1&r=2) <now>')
    assert "<strong>bold</strong>" in out and "<em>it</em>" in out
    assert 'href="https://x.org/?q=1&amp;r=2" target="_blank"' in out
    assert ">a &amp; b</a>" in out and "&lt;now&gt;" in out


def test_safe_url_blocks_unsafe_schemes():
    assert sync_head.safe_url("javascript:alert(1)") == "#"
    assert sync_head.safe_url("") == "#"
    assert sync_head.safe_url("assets/cv.pdf") == "assets/cv.pdf"


def test_rewrite_page_fills_every_static_slot(tmp_path):
    root = _site(tmp_path)
    out = sync_head.rewrite_page(PAGE_HTML, FULL_CONTENT, root, year=2030)
    assert '<a class="nav-name" href="#hero">Sarang S. Bhagwat</a>' in out
    assert '<h1 id="hero-name">Sarang S. Bhagwat</h1>' in out
    assert 'href="assets/Lovelace-Ada_CV.pdf" class="button" download' in out
    assert '<a id="scholar-link" href="https://scholar.example/ada?x=1&amp;y=2">' in out
    assert '<span id="footer-year">2030</span>' in out
    assert 'href="mailto:ada@example.org"><svg' in out
    assert '<link rel="canonical" href="https://ada.example/" />' in out
    assert '<meta property="og:title" content="Sarang S. Bhagwat" />' in out
    assert 'content="Builds tools for BioSTEAM &amp; more."' in out
    assert "Your Name" not in out
    # The hero lines take the marker's indentation.
    assert '\n    <h1 id="hero-name">Sarang S. Bhagwat</h1>\n' in out


def test_rewrite_page_hides_cv_button_without_a_cv(tmp_path):
    out = sync_head.rewrite_page(PAGE_HTML, FULL_CONTENT, _site(tmp_path, cv=False))
    assert '<a id="hero-cv" href="#" class="button" hidden>' in out


def test_rewrite_page_is_idempotent_and_keeps_crlf(tmp_path):
    root = _site(tmp_path)
    crlf = PAGE_HTML.replace("\n", "\r\n")
    once = sync_head.rewrite_page(crlf, FULL_CONTENT, root, year=2030)
    assert sync_head.rewrite_page(once, FULL_CONTENT, root, year=2030) == once
    assert "\n" not in once.replace("\r\n", "")


def test_rewrite_page_raises_when_a_region_is_missing(tmp_path):
    broken = PAGE_HTML.replace("generated:hero", "something-else")
    try:
        sync_head.rewrite_page(broken, FULL_CONTENT, _site(tmp_path))
    except ValueError:
        return
    raise AssertionError("expected ValueError when the hero region is absent")


def test_person_ld_lists_profiles_and_schools():
    ld = sync_head.build_person_ld(FULL_CONTENT, "https://ada.example/", None)
    assert ld["@type"] == "Person" and ld["name"] == "Sarang S. Bhagwat"
    assert ld["sameAs"] == ["https://github.com/ada"]  # mailto is not a profile
    assert [s["name"] for s in ld["alumniOf"]] == ["Uni A", "Uni B"]
    assert ld["affiliation"]["name"] == "University of California, Berkeley"


def test_json_ld_cannot_close_its_script_tag(tmp_path):
    text = FULL_CONTENT.replace('title: "Postdoctoral Researcher"',
                                'title: "</script><b>x"')
    lines = sync_head.build_head_lines(text, _site(tmp_path))
    ld_line = next(l for l in lines if "ld+json" in l)
    assert ld_line.count("</script>") == 1


def test_jpeg_size_reads_real_headshot():
    assert sync_head.jpeg_size(ROOT / "assets" / "headshot.jpg") == (440, 440)


def test_favicon_uses_initials():
    svg = sync_head.build_favicon_svg(CONTENT)
    assert ">SB</text>" in svg
    assert sync_head.build_favicon_svg("meta:\n  title: X\n") is None


def test_rewrite_page_bakes_icons_and_education(tmp_path):
    out = sync_head.rewrite_page(PAGE_HTML, FULL_CONTENT, _site(tmp_path), year=2030)
    assert '<use href="assets/icons.svg#github"/></svg>GitHub</a>' in out
    assert '<use href="assets/icons.svg#email"/></svg>ada@example.org</a>' in out
    assert '<div class="edu-inst">Uni A</div><div class="edu-degree">Ph.D.</div>' in out


def test_read_flow_list_handles_bare_and_escaped_values():
    text = (
        'links:\n'
        '  - { label: GitHub, url: https://github.com/x }\n'
        '  - { label: "Bob\'s \\"site\\"", url: \'https://b.org/it\'\'s\' }\n'
        '  - {}\n'
    )
    assert sync_head.read_flow_list(text, "links") == [
        {"label": "GitHub", "url": "https://github.com/x"},
        {"label": 'Bob\'s "site"', "url": "https://b.org/it's"},
    ]


def test_hero_skips_links_missing_a_label_or_url(tmp_path):
    text = CONTENT + ('  links:\n    - { label: "No URL" }\n'
                      '    - { label: "Ok", url: "https://ok.org" }\n')
    lines = sync_head.build_hero_lines(text, _site(tmp_path))
    assert not any("No URL" in l for l in lines)
    assert any(">Ok</a>" in l for l in lines)


def test_json_ld_escapes_html_comment_openers(tmp_path):
    text = FULL_CONTENT.replace('title: "Postdoctoral Researcher"',
                                'title: "<!--<script> & x"')
    ld_line = next(l for l in sync_head.build_head_lines(text, _site(tmp_path))
                   if "ld+json" in l)
    body = ld_line[ld_line.index(">") + 1:ld_line.rindex("</script>")]
    assert "<" not in body and "&" not in body
    assert json.loads(body)["jobTitle"] == "<!--<script> & x"
