"""Bake the content.yml basics into index.html so it works without JavaScript.

The name, role, institution, tagline, links, and CV live in data/content.yml
like everything else the site shows, and js/main.js renders them at runtime.
Link previews (LinkedIn, Slack, iMessage) and no-JS crawlers never run that
script, so this rewrites the static parts of index.html to match:

- <title> and the meta description;
- the `generated:head` region: canonical link, favicon, Open Graph and Twitter
  card tags, and schema.org Person structured data (JSON-LD);
- the `generated:hero` region: photo, name, title, tagline, CV button, links;
- the `generated:education` region: the Education timeline;
- the nav name, the Google Scholar link, and the footer name.

It also writes assets/favicon.svg, a monogram built from the name's initials.
main.js still re-renders all of it on load, so the two never drift for
visitors with JavaScript. Standard library only; runs locally or in CI
whenever content.yml or assets/ changes. Fails safe: if index.html lacks a tag
or region it expects, the file is left untouched.
"""
from __future__ import annotations

import datetime
import html
import json
import pathlib
import re
import struct
import sys

from site_meta import full_name, read_meta_value

TITLE_RE = re.compile(r"(<title>)(.*?)(</title>)", re.DOTALL)
DESCRIPTION_RE = re.compile(
    r'(<meta\s+name="description"\s+content=")(.*?)(")', re.DOTALL
)
NAV_NAME_RE = re.compile(r'(<a class="nav-name" href="#hero">)(.*?)(</a>)', re.DOTALL)
SCHOLAR_RE = re.compile(r'(<a id="scholar-link" href=")(.*?)(")', re.DOTALL)
FOOTER_YEAR_RE = re.compile(r'(<span id="footer-year">)(.*?)(</span>)', re.DOTALL)
FOOTER_NAME_RE = re.compile(r'(<span id="footer-name">)(.*?)(</span>)', re.DOTALL)

HEADSHOT = "assets/headshot.jpg"
FAVICON = "assets/favicon.svg"
APPLE_TOUCH_ICON = "assets/apple-touch-icon.png"
# Matches --accent in css/style.css so the tab icon reads as part of the site.
FAVICON_BG = "#1a2a4a"
# Link label (lowercased) -> symbol id in assets/icons.svg; mirrors ICON_IDS in
# js/main.js so the pre-rendered links match what main.js renders over them.
ICON_SPRITE = "assets/icons.svg"
ICON_IDS = {
    "google scholar": "scholar",
    "orcid": "orcid",
    "email": "email",
    "github": "github",
    "linkedin": "linkedin",
}


def build_title(content_text: str) -> str | None:
    """The page title: the full display name, or None if it can't be built."""
    return full_name(content_text)


def build_description(content_text: str) -> str | None:
    """One sentence describing the site owner, or None without a name.

    Role and institution are appended the same way the hero subtitle joins them
    in js/main.js. Both are optional, and the sentence simply stops early when
    they are absent. Deliberately no "at the" before the institution: the right
    article depends on the name ("at the University of X" but "at Stanford
    University"), and this file cannot know which applies.
    """
    name = full_name(content_text)
    if not name:
        return None
    affiliation = ", ".join(
        part for part in (read_meta_value(content_text, "title"),
                          read_meta_value(content_text, "institution")) if part
    )
    if affiliation:
        return f"Personal website of {name}, {affiliation}."
    return f"Personal website of {name}."


# --- Reading content.yml without a YAML dependency ------------------------------

# key: "double \"quoted\"" | 'single ''quoted''' | bare scalar (up to , or })
FLOW_PAIR_RE = re.compile(
    r'(\w+):\s*(?:"((?:[^"\\]|\\.)*)"|\'((?:[^\']|\'\')*)\'|([^,}"\']*?))\s*(?=,|\})'
)


def _flow_pairs(item: str) -> dict[str, str]:
    """The key/value pairs of one `{ k: v, ... }` flow mapping."""
    pairs = {}
    for key, dq, sq, bare in FLOW_PAIR_RE.findall(item):
        if dq:
            value = re.sub(r'\\(.)', r'\1', dq)
        elif sq:
            value = sq.replace("''", "'")
        else:
            value = bare.strip()
        pairs[key] = value
    return pairs


def read_flow_list(content_text: str, key: str) -> list[dict[str, str]]:
    """Read a list of one-line `- { k: "v", ... }` mappings under `key:`.

    Covers meta.links and education, which content.yml writes in this flow
    style. The list ends at the first non-blank line indented no deeper than
    the key itself. Items in any other style are skipped.
    """
    lines = content_text.splitlines()
    key_re = re.compile(rf"^([ \t]*){re.escape(key)}:[ \t]*(?:#.*)?$")
    for i, line in enumerate(lines):
        m = key_re.match(line)
        if not m:
            continue
        base = len(m.group(1))
        items = []
        for sub in lines[i + 1:]:
            stripped = sub.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(sub) - len(sub.lstrip())
            if indent < base or (indent == base and not stripped.startswith("-")):
                break
            if stripped.startswith("- {"):
                pairs = _flow_pairs(stripped)
                if pairs:
                    items.append(pairs)
        return items
    return []


def plain_text(text: str) -> str:
    """Markdown-lite (links, **bold**, *italics*) reduced to plain text."""
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1", text or "")
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    return re.sub(r"\*([^*]+)\*", r"\1", s)


# --- HTML builders --------------------------------------------------------------

def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def safe_url(url: str | None) -> str:
    """Mirror of safeUrl() in js/main.js: allow http(s), mailto, relative."""
    u = (url or "").strip()
    if not u:
        return "#"
    if re.match(r"^(https?:|mailto:)", u, re.IGNORECASE):
        return u
    if re.match(r"^[a-z][a-z0-9+.-]*:", u, re.IGNORECASE):
        return "#"
    return u


def anchor(href: str, inner: str, attrs: str = "") -> str:
    """An <a>; off-site links open in a new tab, as markExternalLinks() does."""
    url = safe_url(href)
    ext = ' target="_blank" rel="noopener noreferrer"' if re.match(r"^https?://", url) else ""
    return f'<a{attrs} href="{esc(url)}"{ext}>{inner}</a>'


RICH_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*")


def rich_text(text: str) -> str:
    """Mirror of richText() in js/main.js, producing escaped HTML."""
    out, last = [], 0
    for m in RICH_RE.finditer(text or ""):
        out.append(esc(text[last:m.start()]))
        if m.group(3) is not None:
            out.append(f"<strong>{esc(m.group(3))}</strong>")
        elif m.group(4) is not None:
            out.append(f"<em>{esc(m.group(4))}</em>")
        else:
            out.append(anchor(m.group(2), rich_text(m.group(1))))
        last = m.end()
    out.append(esc((text or "")[last:]))
    return "".join(out)


def icon_svg(label: str, url: str) -> str:
    """Mirror of iconFor()/svgIcon() in js/main.js; empty when no icon applies."""
    icon_id = ICON_IDS.get((label or "").strip().lower())
    if not icon_id and re.match(r"^mailto:", (url or "").strip(), re.IGNORECASE):
        icon_id = ICON_IDS["email"]
    if not icon_id:
        return ""
    return ('<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" '
            'aria-hidden="true" focusable="false">'
            f'<use href="{ICON_SPRITE}#{icon_id}"/></svg>')


def jpeg_size(path: pathlib.Path) -> tuple[int, int] | None:
    """(width, height) of a JPEG, read from its SOF marker; None if unreadable."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        (length,) = struct.unpack(">H", data[i + 2:i + 4])
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return width, height
        i += 2 + length
    return None


def read_site_url(root: pathlib.Path) -> str | None:
    """https://<domain>/ from the GitHub Pages CNAME file, or None."""
    try:
        domain = (root / "CNAME").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return f"https://{domain}/" if domain else None


def read_cv_path(root: pathlib.Path) -> str | None:
    """The CV path recorded by detect_cv.py in data/cv.json, or None."""
    try:
        doc = json.loads((root / "data" / "cv.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc.get("file") if isinstance(doc, dict) else None


def build_favicon_svg(content_text: str) -> str | None:
    """A round monogram of the first and last initials, or None without a name."""
    first = read_meta_value(content_text, "first_name")
    last = read_meta_value(content_text, "last_name")
    if not (first and last):
        return None
    initials = esc((first[0] + last[0]).upper())
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<circle cx="32" cy="32" r="32" fill="{FAVICON_BG}"/>'
        '<text x="32" y="33" text-anchor="middle" dominant-baseline="central" '
        'font-family="Georgia, \'Times New Roman\', serif" font-size="28" '
        f'font-weight="600" fill="#ffffff">{initials}</text></svg>\n'
    )


def build_person_ld(content_text: str, site_url: str | None,
                    image_url: str | None) -> dict:
    """schema.org Person for search engines, from the same fields the page shows."""
    name = full_name(content_text)
    person: dict = {"@context": "https://schema.org", "@type": "Person", "name": name}
    for field, key in (("givenName", "first_name"), ("familyName", "last_name"),
                       ("jobTitle", "title")):
        value = read_meta_value(content_text, key)
        if value:
            person[field] = value
    institution = read_meta_value(content_text, "institution")
    if institution:
        person["affiliation"] = {"@type": "Organization", "name": institution}
    tagline = read_meta_value(content_text, "tagline")
    if tagline:
        person["description"] = plain_text(tagline)
    if site_url:
        person["url"] = site_url
    if image_url:
        person["image"] = image_url
    email = read_meta_value(content_text, "email")
    if email:
        person["email"] = f"mailto:{email}"
    same_as = [l["url"] for l in read_flow_list(content_text, "links")
               if re.match(r"^https?://", l.get("url", ""))]
    if same_as:
        person["sameAs"] = same_as
    schools = []
    for e in read_flow_list(content_text, "education"):
        inst = e.get("institution")
        if inst and inst not in schools:
            schools.append(inst)
    if schools:
        person["alumniOf"] = [{"@type": "CollegeOrUniversity", "name": s} for s in schools]
    return person


def build_head_lines(content_text: str, root: pathlib.Path) -> list[str]:
    """Lines for the generated:head region (unindented)."""
    name = full_name(content_text) or ""
    site_url = read_site_url(root)
    tagline = read_meta_value(content_text, "tagline")
    summary = plain_text(tagline) if tagline else (build_description(content_text) or "")
    size = jpeg_size(root / HEADSHOT)
    image_url = f"{site_url}{HEADSHOT}" if site_url and size else None

    lines = []
    if site_url:
        lines.append(f'<link rel="canonical" href="{esc(site_url)}" />')
    lines.append(f'<link rel="icon" href="{FAVICON}" type="image/svg+xml" />')
    if (root / APPLE_TOUCH_ICON).exists():
        lines.append(f'<link rel="apple-touch-icon" href="{APPLE_TOUCH_ICON}" />')
    lines += [
        '<meta property="og:type" content="profile" />',
        f'<meta property="og:title" content="{esc(name)}" />',
        f'<meta property="og:description" content="{esc(summary)}" />',
    ]
    if site_url:
        lines.append(f'<meta property="og:url" content="{esc(site_url)}" />')
    if image_url:
        lines += [
            f'<meta property="og:image" content="{esc(image_url)}" />',
            f'<meta property="og:image:width" content="{size[0]}" />',
            f'<meta property="og:image:height" content="{size[1]}" />',
            f'<meta property="og:image:alt" content="{esc(name)}" />',
        ]
    for prop, key in (("profile:first_name", "first_name"), ("profile:last_name", "last_name")):
        value = read_meta_value(content_text, key)
        if value:
            lines.append(f'<meta property="{prop}" content="{esc(value)}" />')
    lines.append('<meta name="twitter:card" content="summary" />')
    # <, > and & are \u-escaped (still valid JSON) so no value can close the
    # <script> element early or switch the parser into an escaped state.
    ld = (json.dumps(build_person_ld(content_text, site_url, image_url),
                     ensure_ascii=False, separators=(",", ":"))
          .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))
    lines.append(f'<script type="application/ld+json">{ld}</script>')
    return lines


def build_hero_lines(content_text: str, root: pathlib.Path) -> list[str]:
    """Lines for the generated:hero region (unindented), mirroring renderContent()."""
    name = full_name(content_text) or ""
    title = read_meta_value(content_text, "title")
    institution = read_meta_value(content_text, "institution")
    tagline = read_meta_value(content_text, "tagline") or ""
    size = jpeg_size(root / HEADSHOT)
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ""

    subtitle = esc(title) if title else ""
    if title and institution:
        subtitle += ", "
    if institution:
        subtitle += f'<span class="hero-inst">{esc(institution)}</span>'

    cv = read_cv_path(root)
    cv_link = (f'<a id="hero-cv" href="{esc(safe_url(cv))}" class="button" download>Download CV</a>'
               if cv else '<a id="hero-cv" href="#" class="button" hidden>Download CV</a>')

    lines = [
        f'<img id="hero-photo" src="{HEADSHOT}"{dims} alt="{esc(name)}" fetchpriority="high" />',
        f'<h1 id="hero-name">{esc(name)}</h1>',
        f'<p id="hero-title">{subtitle}</p>',
        f'<p id="hero-tagline">{rich_text(tagline)}</p>',
        '<div class="hero-footer">',
        '  <p class="hero-actions">',
        f'    {cv_link}',
        '  </p>',
        '  <ul id="hero-links" class="icon-links">',
    ]
    for link in read_flow_list(content_text, "links"):
        label, url = link.get("label", ""), link.get("url", "")
        if not (label and url):  # an empty link is worse than none
            continue
        inner = icon_svg(label, url) + esc(label)
        lines.append(f'    <li>{anchor(url, inner, ' class="icon-link"')}</li>')
    lines += ['  </ul>', '</div>']
    return lines


def build_education_lines(content_text: str) -> list[str]:
    """Lines for the generated:education region, mirroring renderContent()."""
    return [
        '<li class="edu-item">'
        f'<span class="edu-year">{esc(e.get("year", ""))}</span>'
        f'<div class="edu-inst">{esc(e.get("institution", ""))}</div>'
        f'<div class="edu-degree">{esc(e.get("degree", ""))}</div></li>'
        for e in read_flow_list(content_text, "education")
    ]


# --- Rewriting index.html -------------------------------------------------------

def _replace_one(pattern: re.Pattern, value: str, text: str, label: str,
                 escape: bool = True) -> str:
    """Substitute the single tag `pattern` matches, escaping `value` first.

    A lambda supplies the replacement so backslashes and group references in a
    name can't be interpreted as substitution syntax.
    """
    new_value = html.escape(value, quote=True) if escape else value
    new_text, count = pattern.subn(
        lambda m: m.group(1) + new_value + m.group(3), text, count=1
    )
    if count == 0:
        raise ValueError(f"no {label} tag found in index.html")
    return new_text


def replace_region(text: str, region: str, lines: list[str]) -> str:
    """Replace everything between `<!-- generated:REGION -->` and its closer.

    The new lines are indented to match the opening marker and use the file's
    own line endings, so regenerating is idempotent and keeps CRLF files CRLF.
    """
    pattern = re.compile(
        rf"([ \t]*)(<!-- generated:{re.escape(region)} [^>]*-->)(\r?\n)(.*?)"
        rf"([ \t]*<!-- /generated:{re.escape(region)} -->)",
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        raise ValueError(f"no generated:{region} region found in index.html")
    indent, nl = m.group(1), m.group(3)
    body = "".join(f"{indent}{line}{nl}" if line else nl for line in lines)
    return text[:m.start(4)] + body + text[m.end(4):]


def rewrite_head(html_text: str, title: str, description: str) -> str:
    """Return index.html with the title and description tag contents replaced."""
    out = _replace_one(TITLE_RE, title, html_text, "<title>")
    return _replace_one(DESCRIPTION_RE, description, out, 'meta name="description"')


def rewrite_page(html_text: str, content_text: str, root: pathlib.Path,
                 year: int | None = None) -> str:
    """Return index.html with every generated tag and region rewritten."""
    name = full_name(content_text) or ""
    out = rewrite_head(html_text, build_title(content_text) or "",
                       build_description(content_text) or "")
    out = replace_region(out, "head", build_head_lines(content_text, root))
    out = replace_region(out, "hero", build_hero_lines(content_text, root))
    out = replace_region(out, "education", build_education_lines(content_text))
    out = _replace_one(NAV_NAME_RE, name, out, "nav-name")
    scholar = read_meta_value(content_text, "scholar_url")
    out = _replace_one(SCHOLAR_RE, safe_url(scholar), out, "scholar-link")
    out = _replace_one(FOOTER_YEAR_RE, str(year or datetime.date.today().year),
                       out, "footer-year")
    return _replace_one(FOOTER_NAME_RE, name, out, "footer-name")


def read_html(path: pathlib.Path) -> str:
    """Read a file preserving its line endings verbatim (no translation)."""
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write_index(new_html: str, out_path: pathlib.Path) -> bool:
    """Write a file verbatim, returning True only if the content changed."""
    if out_path.exists() and read_html(out_path) == new_html:
        return False
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(new_html)
    return True


def main(argv=None) -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    content_path = root / "data" / "content.yml"
    index_path = root / "index.html"

    text = content_path.read_text(encoding="utf-8")
    title = build_title(text)
    description = build_description(text)

    if not (title and description):
        print("warning: first_name/last_name missing in content.yml; "
              "leaving index.html unchanged", file=sys.stderr)
        return 0

    try:
        new_html = rewrite_page(read_html(index_path), text, root)
    except ValueError as err:  # fail-safe: never mangle a live page
        print(f"warning: {err}; leaving index.html unchanged", file=sys.stderr)
        return 0

    changed = write_index(new_html, index_path)
    favicon = build_favicon_svg(text)
    icon_changed = bool(favicon) and write_index(favicon, root / FAVICON)
    print(f"{'updated' if changed else 'no change'}: index.html (title = {title}); "
          f"{'updated' if icon_changed else 'no change'}: {FAVICON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
