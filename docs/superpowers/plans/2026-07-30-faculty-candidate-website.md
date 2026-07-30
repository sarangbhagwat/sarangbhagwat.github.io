# Faculty Candidate Personal Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-page personal website for a Chemical Engineering faculty candidate, with publications that auto-update from ORCID.

**Architecture:** A dependency-free static site (HTML + CSS + vanilla JS) served by GitHub Pages. Author-edited prose lives in one YAML file parsed in the browser. Publications are refreshed by a scheduled GitHub Action that runs a standard-library-only Python script, which fetches the ORCID public API and commits `data/publications.json`; the page renders that static JSON at load.

**Tech Stack:** HTML5, CSS3, vanilla JavaScript (ES modules), a vendored `js-yaml` parser (single static file), Python 3 standard library (`urllib`, `json`, `re`) for the sync script, `pytest` for sync tests, GitHub Actions for scheduling, GitHub Pages for hosting.

## Global Constraints

- Local Python interpreter (tests + local run): `C:\Users\saran\anaconda3\envs\current_env\python.exe` (Python 3.14.6, `pytest` 9.1.1 installed). Referred to below as `$PY`; each PowerShell task begins by setting `$PY = "C:\Users\saran\anaconda3\envs\current_env\python.exe"`.
- Sync script (`scripts/sync_orcid.py`) MUST use only the Python standard library — no `requests`, no `pyyaml`, no third-party imports. This keeps the GitHub Action dependency-free.
- No local Node.js. No JS build step, no bundler, no npm. All JS is hand-written and loaded directly; third-party JS (js-yaml) is vendored as a committed static file.
- The author edits only `data/content.yml`, `assets/headshot.jpg`, and `assets/cv.pdf`. `data/publications.json` is machine-generated and never hand-edited.
- Publications sync is fail-safe: any fetch/parse error leaves the existing `data/publications.json` untouched so the live page never breaks.
- Visual style: classic academic — serif headings, sans-serif body, deep-navy accent (`#1a2a4a`), off-white background, single centered column ~720px, fully responsive, no analytics/trackers.
- Fonts are self-hosted (no font-CDN calls at runtime).
- Commit after every task with the exact message shown.
- Local static serving for browser verification: `& $PY -m http.server 8000` from the repo root, then browse `http://localhost:8000`. `fetch()` of `.yml`/`.json` requires HTTP (not `file://`).
- Git is already initialized in the repo root; `.superpowers/` is gitignored.

---

## File Structure

Created across the tasks below:

```
/
├── index.html                        # Task 1 — semantic page skeleton + sections
├── css/
│   └── style.css                     # Task 1 (skeleton) → Task 6 (full classic-academic design)
├── js/
│   ├── main.js                       # Task 2 (content) → Task 5 (publications) → Task 7 (nav)
│   └── vendor/
│       └── js-yaml.min.js            # Task 2 — vendored YAML parser (downloaded static file)
├── fonts/                            # Task 6 — self-hosted serif + sans woff2 files
├── data/
│   ├── content.yml                   # Task 2 — author-edited content (placeholders shipped)
│   └── publications.json             # Task 4 — generated snapshot (placeholder shipped, then real)
├── assets/
│   ├── headshot.jpg                  # Task 9 — placeholder image, author replaces
│   └── cv.pdf                        # Task 9 — placeholder pdf, author replaces
├── scripts/
│   └── sync_orcid.py                 # Tasks 3–4 — stdlib-only ORCID → publications.json
├── tests/
│   ├── test_sync_orcid.py            # Tasks 3–4 — pytest unit tests
│   └── fixtures/
│       ├── orcid_works_summary.json  # Task 3 — sample ORCID works-summary response
│       └── orcid_work_detail.json    # Task 4 — sample ORCID single-work detail response
├── .github/
│   └── workflows/
│       └── update-publications.yml   # Task 8 — scheduled + manual sync workflow
├── .nojekyll                         # Task 9 — disable Jekyll processing on Pages
├── CNAME                             # Task 9 — custom domain
└── README.md                         # Task 9 — how to edit content, deploy, configure DNS
```

Responsibility boundaries: `index.html` is structure only; `css/style.css` is all presentation; `js/main.js` is all client behavior (content population, publications rendering, nav); `scripts/sync_orcid.py` is the only server-side/build code and is pure Python stdlib with small, individually testable functions.

---

## Task 1: Page skeleton and local serve harness

**Files:**
- Create: `index.html`
- Create: `css/style.css`

**Interfaces:**
- Consumes: nothing.
- Produces: DOM element IDs that later tasks populate — `#site-nav`, and sections with IDs `#hero`, `#about`, `#research`, `#publications`, `#teaching`, `#awards`, `#contact`. Hero placeholders: `#hero-name`, `#hero-title`, `#hero-tagline`, `#hero-photo`, `#hero-cv`, `#hero-links`. Section content containers: `#about-body`, `#education-list`, `#research-list`, `#publications-list`, `#scholar-link`, `#teaching-philosophy`, `#teaching-courses`, `#awards-list`, `#contact-list`.

- [ ] **Step 1: Create the HTML skeleton**

Create `index.html`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Faculty Candidate — Personal Website</title>
  <meta name="description" content="Personal website of a Chemical Engineering faculty candidate." />
  <link rel="stylesheet" href="css/style.css" />
</head>
<body>
  <header id="site-header">
    <nav id="site-nav" aria-label="Primary">
      <a class="nav-name" href="#hero">Your Name</a>
      <ul class="nav-links">
        <li><a href="#about">About</a></li>
        <li><a href="#research">Research</a></li>
        <li><a href="#publications">Publications</a></li>
        <li><a href="#teaching">Teaching</a></li>
        <li><a href="#awards">Awards</a></li>
        <li><a href="#contact">Contact</a></li>
      </ul>
    </nav>
  </header>

  <main>
    <section id="hero">
      <img id="hero-photo" alt="" />
      <h1 id="hero-name"></h1>
      <p id="hero-title"></p>
      <p id="hero-tagline"></p>
      <p class="hero-actions">
        <a id="hero-cv" href="#" class="button">Download CV</a>
      </p>
      <ul id="hero-links" class="icon-links"></ul>
    </section>

    <section id="about">
      <h2>About</h2>
      <div id="about-body"></div>
      <h3>Education</h3>
      <ul id="education-list"></ul>
    </section>

    <section id="research">
      <h2>Research interests</h2>
      <div id="research-list"></div>
    </section>

    <section id="publications">
      <h2>Publications</h2>
      <p><a id="scholar-link" href="#">See all on Google Scholar</a></p>
      <div id="publications-list"></div>
    </section>

    <section id="teaching">
      <h2>Teaching</h2>
      <div id="teaching-philosophy"></div>
      <h3>Courses</h3>
      <ul id="teaching-courses"></ul>
    </section>

    <section id="awards">
      <h2>Awards and honors</h2>
      <ul id="awards-list"></ul>
    </section>

    <section id="contact">
      <h2>Contact</h2>
      <ul id="contact-list"></ul>
    </section>
  </main>

  <footer id="site-footer">
    <p>&copy; <span id="footer-year"></span> <span id="footer-name"></span></p>
  </footer>

  <script type="module" src="js/main.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create a minimal stylesheet placeholder**

Create `css/style.css` (full design comes in Task 6; this just makes the skeleton legible):

```css
:root { --accent: #1a2a4a; --bg: #fbfaf7; --text: #1c1c1a; --muted: #5f5e5a; --max: 720px; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; line-height: 1.6; }
nav { display: flex; justify-content: space-between; align-items: center; max-width: var(--max); margin: 0 auto; padding: 1rem; }
main { max-width: var(--max); margin: 0 auto; padding: 0 1rem; }
section { padding: 2rem 0; border-top: 1px solid #e6e3dc; }
h1, h2, h3 { color: var(--accent); }
.nav-links { display: flex; gap: 1rem; list-style: none; margin: 0; padding: 0; }
a { color: var(--accent); }
```

- [ ] **Step 3: Serve the site locally**

Run (PowerShell, from repo root):

```powershell
$PY = "C:\Users\saran\anaconda3\envs\current_env\python.exe"
Start-Process -NoNewWindow $PY -ArgumentList "-m","http.server","8000"
```

(Executing agent: start this with `run_in_background: true` instead, or stop it after verifying.)

- [ ] **Step 4: Verify the skeleton renders**

Use the browser tools: navigate to `http://localhost:8000`, then `get_page_text`.
Expected: the page shows the nav (About, Research, Publications, Teaching, Awards, Contact) and the section headings "About", "Research interests", "Publications", "Teaching", "Awards and honors", "Contact". Content areas are empty (populated in later tasks). No console errors except a 404 for `js/main.js` (created next task) — acceptable at this step.

- [ ] **Step 5: Commit**

```bash
git add index.html css/style.css
git commit -m "feat: add page skeleton and section structure"
```

---

## Task 2: Content model and browser-side rendering

**Files:**
- Create: `data/content.yml`
- Create: `js/vendor/js-yaml.min.js` (downloaded)
- Create: `js/main.js`

**Interfaces:**
- Consumes: DOM IDs from Task 1.
- Produces: the `content.yml` schema (below) and, in `js/main.js`, the functions `loadContent()` → returns parsed object, and `renderContent(data)` → populates hero/about/education/research/teaching/awards/contact and the footer. `main.js` calls both on `DOMContentLoaded`. Later tasks add `renderPublications()` and nav behavior to this same file.

- [ ] **Step 1: Create the content file with placeholders**

Create `data/content.yml`:

```yaml
# Edit this file to update your website. After saving, refresh the page.
# The publications list is generated automatically from ORCID — do not edit it here.
meta:
  name: "Your Name"
  title: "Postdoctoral Researcher"
  institution: "Your University"
  tagline: "One-line summary of your research focus."
  email: "you@example.com"
  orcid_id: "0000-0002-1825-0097"          # your ORCID iD — drives the publications sync
  scholar_url: "https://scholar.google.com/citations?user=REPLACE_ME"
  links:
    - { label: "Google Scholar", url: "https://scholar.google.com/citations?user=REPLACE_ME" }
    - { label: "ORCID", url: "https://orcid.org/0000-0002-1825-0097" }
    - { label: "Email", url: "mailto:you@example.com" }
about:
  - "First paragraph about you: your current role, where, and your overarching research vision."
  - "Second paragraph: your trajectory and what motivates your work."
education:
  - { degree: "Ph.D., Chemical Engineering", institution: "University Name", year: "20XX" }
  - { degree: "B.S., Chemical Engineering", institution: "University Name", year: "20XX" }
research_interests:
  - { heading: "Research theme one", body: "One or two sentences describing this theme." }
  - { heading: "Research theme two", body: "One or two sentences describing this theme." }
  - { heading: "Research theme three", body: "One or two sentences describing this theme." }
teaching:
  philosophy: "A short paragraph on your teaching philosophy and approach to mentoring."
  courses:
    - "Course you have taught or could teach"
    - "Another course"
awards:
  - { year: "20XX", description: "Fellowship, award, or honor" }
  - { year: "20XX", description: "Another award" }
```

- [ ] **Step 2: Vendor the js-yaml parser**

Download the parser into `js/vendor/` (PowerShell, from repo root):

```powershell
New-Item -ItemType Directory -Force js\vendor | Out-Null
Invoke-WebRequest -Uri "https://cdnjs.cloudflare.com/ajax/libs/js-yaml/4.1.0/js-yaml.min.js" -OutFile "js\vendor\js-yaml.min.js"
```

Expected: `js/vendor/js-yaml.min.js` exists and is ~30–40 KB. This file is committed and loaded directly; no CDN call happens at runtime.

- [ ] **Step 3: Write main.js content loading and rendering**

Create `js/main.js`:

```js
import "./vendor/js-yaml.min.js"; // exposes global `jsyaml`

async function loadContent() {
  const res = await fetch("data/content.yml", { cache: "no-cache" });
  if (!res.ok) throw new Error(`content.yml HTTP ${res.status}`);
  const text = await res.text();
  return window.jsyaml.load(text);
}

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  for (const c of [].concat(children)) node.append(c);
  return node;
}

function renderContent(data) {
  const m = data.meta || {};
  document.title = `${m.name} — ${m.title}`;
  document.querySelector(".nav-name").textContent = m.name || "";
  document.getElementById("hero-name").textContent = m.name || "";
  document.getElementById("hero-title").textContent =
    [m.title, m.institution].filter(Boolean).join(", ");
  document.getElementById("hero-tagline").textContent = m.tagline || "";

  const cv = document.getElementById("hero-cv");
  cv.href = "assets/cv.pdf";
  cv.setAttribute("download", "");

  const heroLinks = document.getElementById("hero-links");
  heroLinks.replaceChildren(
    ...(m.links || []).map((l) =>
      el("li", {}, el("a", { href: l.url, textContent: l.label }))
    )
  );

  document.getElementById("about-body").replaceChildren(
    ...(data.about || []).map((p) => el("p", { textContent: p }))
  );

  document.getElementById("education-list").replaceChildren(
    ...(data.education || []).map((e) =>
      el("li", { textContent: `${e.degree}, ${e.institution} (${e.year})` })
    )
  );

  document.getElementById("research-list").replaceChildren(
    ...(data.research_interests || []).map((r) =>
      el("div", { className: "research-item" }, [
        el("h3", { textContent: r.heading }),
        el("p", { textContent: r.body }),
      ])
    )
  );

  const scholar = document.getElementById("scholar-link");
  if (m.scholar_url) scholar.href = m.scholar_url;

  const teaching = data.teaching || {};
  document.getElementById("teaching-philosophy").replaceChildren(
    el("p", { textContent: teaching.philosophy || "" })
  );
  document.getElementById("teaching-courses").replaceChildren(
    ...(teaching.courses || []).map((c) => el("li", { textContent: c }))
  );

  document.getElementById("awards-list").replaceChildren(
    ...(data.awards || []).map((a) =>
      el("li", {}, [el("strong", { textContent: `${a.year} ` }), a.description])
    )
  );

  document.getElementById("contact-list").replaceChildren(
    ...(m.links || []).map((l) =>
      el("li", {}, el("a", { href: l.url, textContent: l.label }))
    )
  );

  document.getElementById("footer-year").textContent = new Date().getFullYear();
  document.getElementById("footer-name").textContent = m.name || "";
}

async function init() {
  try {
    const data = await loadContent();
    renderContent(data);
    // Task 5 will call renderPublications() here.
    // Task 7 will initialize nav behavior here.
    window.__content = data; // exposed for later tasks
  } catch (err) {
    console.error(err);
  }
}

document.addEventListener("DOMContentLoaded", init);
```

Note: `import "./vendor/js-yaml.min.js"` runs the UMD file for its side effect of defining the `window.jsyaml` global; it has no ES exports, which is fine.

- [ ] **Step 4: Verify content renders in the browser**

Serve (`& $PY -m http.server 8000`) and navigate to `http://localhost:8000`. Use `get_page_text`.
Expected: hero shows "Your Name", "Postdoctoral Researcher, Your University", the tagline; About shows two placeholder paragraphs; Education shows two degree lines; Research shows three themes; Teaching shows the philosophy and two courses; Awards shows two dated entries; Contact shows three links. Check `read_console_messages` — no errors.

- [ ] **Step 5: Commit**

```bash
git add data/content.yml js/vendor/js-yaml.min.js js/main.js
git commit -m "feat: render author content from content.yml"
```

---

## Task 3: ORCID sync — pure parsing functions (TDD)

**Files:**
- Create: `scripts/sync_orcid.py`
- Create: `tests/test_sync_orcid.py`
- Create: `tests/fixtures/orcid_works_summary.json`

**Interfaces:**
- Consumes: nothing (pure functions).
- Produces: in `scripts/sync_orcid.py` — `read_orcid_id(content_yml_text: str) -> str`; `extract_doi(external_ids: dict) -> tuple[str | None, str | None]` returning `(doi, url)`; `parse_work_summary(summary: dict) -> dict` returning a publication dict `{title, venue, year, type, doi, url, put_code}` (authors added in Task 4); `parse_works_summary_response(raw: dict) -> list[dict]` returning parsed, de-duplicated publications sorted newest-first.

- [ ] **Step 1: Create the ORCID works-summary fixture**

Create `tests/fixtures/orcid_works_summary.json`:

```json
{
  "group": [
    {
      "work-summary": [
        {
          "put-code": 111,
          "title": { "title": { "value": "Catalytic conversion of biomass" } },
          "journal-title": { "value": "Nature Catalysis" },
          "publication-date": { "year": { "value": "2023" } },
          "type": "journal-article",
          "external-ids": {
            "external-id": [
              {
                "external-id-type": "doi",
                "external-id-value": "10.1000/abc123",
                "external-id-url": { "value": "https://doi.org/10.1000/abc123" },
                "external-id-relationship": "self"
              }
            ]
          }
        }
      ]
    },
    {
      "work-summary": [
        {
          "put-code": 222,
          "title": { "title": { "value": "Reaction networks for sustainable fuels" } },
          "journal-title": { "value": "AIChE Journal" },
          "publication-date": { "year": { "value": "2021" } },
          "type": "journal-article",
          "external-ids": { "external-id": [] }
        }
      ]
    },
    {
      "work-summary": [
        {
          "put-code": 333,
          "title": { "title": { "value": "No date preprint" } },
          "journal-title": null,
          "publication-date": null,
          "type": "preprint",
          "external-ids": {
            "external-id": [
              {
                "external-id-type": "doi",
                "external-id-value": "10.1000/xyz789",
                "external-id-url": { "value": "https://doi.org/10.1000/xyz789" },
                "external-id-relationship": "self"
              }
            ]
          }
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_sync_orcid.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```powershell
$PY = "C:\Users\saran\anaconda3\envs\current_env\python.exe"
& $PY -m pytest tests/test_sync_orcid.py -v
```

Expected: collection error / FAIL — `sync_orcid` module or functions not defined.

- [ ] **Step 4: Implement the pure functions**

Create `scripts/sync_orcid.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```powershell
$PY = "C:\Users\saran\anaconda3\envs\current_env\python.exe"
& $PY -m pytest tests/test_sync_orcid.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/sync_orcid.py tests/test_sync_orcid.py tests/fixtures/orcid_works_summary.json
git commit -m "feat: parse ORCID works-summary into publication records"
```

---

## Task 4: ORCID sync — fetch, authors, fail-safe write, CLI

**Files:**
- Modify: `scripts/sync_orcid.py`
- Modify: `tests/test_sync_orcid.py`
- Create: `tests/fixtures/orcid_work_detail.json`
- Create: `data/publications.json` (generated)

**Interfaces:**
- Consumes: functions from Task 3.
- Produces: `fetch_json(url: str, timeout: int = 20) -> dict` (urllib GET with ORCID JSON `Accept` header); `parse_contributors(work_detail: dict) -> list[str]`; `build_publications(orcid_id, *, opener=fetch_json) -> dict` returning the full publications document `{generated_at, orcid_id, publications: [...]}`; `write_publications_atomic(doc: dict, out_path) -> bool` (writes only if content changed; returns True if written); and a `main(argv)` CLI. `opener` is injectable so tests avoid network.

- [ ] **Step 1: Create the single-work-detail fixture**

Create `tests/fixtures/orcid_work_detail.json`:

```json
{
  "contributors": {
    "contributor": [
      { "credit-name": { "value": "Your Name" } },
      { "credit-name": { "value": "Coauthor One" } },
      { "credit-name": { "value": "Coauthor Two" } }
    ]
  }
}
```

- [ ] **Step 2: Write failing tests for the new behavior**

Append to `tests/test_sync_orcid.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```powershell
$PY = "C:\Users\saran\anaconda3\envs\current_env\python.exe"
& $PY -m pytest tests/test_sync_orcid.py -v
```

Expected: the 4 new tests FAIL (functions not defined); the Task 3 tests still PASS.

- [ ] **Step 4: Implement fetch, authors, build, write, and CLI**

Append to `scripts/sync_orcid.py`:

```python
import datetime
import pathlib
import sys
import urllib.request

ORCID_API = "https://pub.orcid.org/v3.0"


def fetch_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_contributors(work_detail: dict) -> list[str]:
    contributors = (work_detail.get("contributors") or {}).get("contributor", []) or []
    names = []
    for c in contributors:
        name = (c.get("credit-name") or {}).get("value")
        if name:
            names.append(name)
    return names


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
        except Exception:
            pub["authors"] = []  # authors are best-effort
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "orcid_id": orcid_id,
        "publications": pubs,
    }


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
        doc = build_publications(orcid_id)
    except Exception as err:  # fail-safe: never clobber the live list
        print(f"sync failed, keeping existing publications.json: {err}",
              file=sys.stderr)
        return 0

    changed = write_publications_atomic(doc, out_path)
    print(f"{'updated' if changed else 'no change'}: "
          f"{len(doc['publications'])} publications")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the full test suite to verify it passes**

```powershell
$PY = "C:\Users\saran\anaconda3\envs\current_env\python.exe"
& $PY -m pytest tests/ -v
```

Expected: all 10 tests PASS.

- [ ] **Step 6: Generate the initial publications.json**

Run the script against the placeholder ORCID iD in `content.yml` (the sample iD `0000-0002-1825-0097` resolves to a real public record, so this produces a valid file to develop against):

```powershell
$PY = "C:\Users\saran\anaconda3\envs\current_env\python.exe"
& $PY scripts/sync_orcid.py
```

Expected: prints `updated: N publications` and creates `data/publications.json` with a `publications` array. If the network is unavailable, create `data/publications.json` manually with `{"generated_at":"","orcid_id":"0000-0002-1825-0097","publications":[]}` so later tasks have a file to fetch.

- [ ] **Step 7: Commit**

```bash
git add scripts/sync_orcid.py tests/test_sync_orcid.py tests/fixtures/orcid_work_detail.json data/publications.json
git commit -m "feat: fetch ORCID works with authors and write publications.json"
```

---

## Task 5: Render publications on the page

**Files:**
- Modify: `js/main.js`

**Interfaces:**
- Consumes: `data/publications.json` (schema from Task 4), the `#publications-list` container and `el()` helper from Task 2.
- Produces: `loadPublications()` → parsed doc; `renderPublications(doc, selfName)` → fills `#publications-list` grouped by year (newest first), bolding the author's own name. `init()` calls these after `renderContent()`.

- [ ] **Step 1: Add publications loading and rendering to main.js**

In `js/main.js`, add these functions above `init()`:

```js
async function loadPublications() {
  const res = await fetch("data/publications.json", { cache: "no-cache" });
  if (!res.ok) throw new Error(`publications.json HTTP ${res.status}`);
  return res.json();
}

function authorsFragment(authors, selfName) {
  const frag = document.createDocumentFragment();
  authors.forEach((name, i) => {
    if (i > 0) frag.append(", ");
    const isSelf = selfName && name.toLowerCase() === selfName.toLowerCase();
    frag.append(el(isSelf ? "strong" : "span", { textContent: name }));
  });
  return frag;
}

function renderPublications(doc, selfName) {
  const list = document.getElementById("publications-list");
  const pubs = (doc && doc.publications) || [];
  if (pubs.length === 0) {
    list.replaceChildren(el("p", { className: "muted", textContent:
      "Publications will appear here once the ORCID sync runs." }));
    return;
  }
  const byYear = new Map();
  for (const p of pubs) {
    const y = p.year || "Undated";
    if (!byYear.has(y)) byYear.set(y, []);
    byYear.get(y).push(p);
  }
  const years = [...byYear.keys()].sort((a, b) => {
    if (a === "Undated") return 1;
    if (b === "Undated") return -1;
    return b - a;
  });
  const blocks = [];
  for (const y of years) {
    blocks.push(el("h3", { className: "pub-year", textContent: String(y) }));
    const items = byYear.get(y).map((p) => {
      const li = el("li", { className: "pub-item" });
      li.append(el("span", { className: "pub-title", textContent: p.title || "Untitled" }));
      if (p.authors && p.authors.length) {
        li.append(el("div", { className: "pub-authors" }, authorsFragment(p.authors, selfName)));
      }
      const meta = [p.venue, p.year].filter(Boolean).join(", ");
      if (meta) li.append(el("div", { className: "pub-venue", textContent: meta }));
      if (p.url) li.append(el("a", { className: "pub-doi", href: p.url, textContent: "DOI" }));
      return li;
    });
    blocks.push(el("ul", { className: "pub-list" }, items));
  }
  list.replaceChildren(...blocks);
}
```

- [ ] **Step 2: Call publications rendering from init()**

In `js/main.js`, update `init()`:

```js
async function init() {
  try {
    const data = await loadContent();
    renderContent(data);
    window.__content = data;
    try {
      const pubs = await loadPublications();
      renderPublications(pubs, (data.meta || {}).name);
    } catch (pubErr) {
      console.error(pubErr);
      renderPublications({ publications: [] }, (data.meta || {}).name);
    }
    // Task 7 will initialize nav behavior here.
  } catch (err) {
    console.error(err);
  }
}
```

- [ ] **Step 3: Verify publications render in the browser**

Serve (`& $PY -m http.server 8000`), navigate to `http://localhost:8000`, `get_page_text`.
Expected: the Publications section shows year subheadings (e.g. "2023", "2021") with entries beneath, each showing a title, optional authors, "Venue, Year", and a "DOI" link where present. If `publications.json` has an empty array, the fallback message appears instead. Check `read_console_messages` — no errors.

- [ ] **Step 4: Commit**

```bash
git add js/main.js
git commit -m "feat: render publications grouped by year"
```

---

## Task 6: Classic academic visual design

**Files:**
- Modify: `css/style.css`
- Create: `fonts/` (self-hosted woff2 files)

**Interfaces:**
- Consumes: all DOM structure and classes from Tasks 1, 2, 5 (`.nav-name`, `.nav-links`, `#hero-photo`, `.button`, `.icon-links`, `.research-item`, `.pub-year`, `.pub-item`, `.pub-title`, `.pub-authors`, `.pub-venue`, `.pub-doi`, `.muted`).
- Produces: the final stylesheet. No new JS interfaces.

- [ ] **Step 1: Self-host the fonts**

Download a serif (headings) and a sans (body) as woff2 into `fonts/` (PowerShell, from repo root):

```powershell
New-Item -ItemType Directory -Force fonts | Out-Null
Invoke-WebRequest "https://cdn.jsdelivr.net/fontsource/fonts/source-serif-4@latest/latin-600-normal.woff2" -OutFile "fonts/source-serif-4-600.woff2"
Invoke-WebRequest "https://cdn.jsdelivr.net/fontsource/fonts/source-sans-3@latest/latin-400-normal.woff2" -OutFile "fonts/source-sans-3-400.woff2"
Invoke-WebRequest "https://cdn.jsdelivr.net/fontsource/fonts/source-sans-3@latest/latin-600-normal.woff2" -OutFile "fonts/source-sans-3-600.woff2"
```

Expected: three `.woff2` files in `fonts/`. If any URL 404s, substitute the equivalent `@fontsource` woff2 path from jsdelivr; the design tolerates any clean serif/sans pair.

- [ ] **Step 2: Write the full stylesheet**

Replace `css/style.css` entirely:

```css
@font-face { font-family: "Site Serif"; src: url("../fonts/source-serif-4-600.woff2") format("woff2"); font-weight: 600; font-display: swap; }
@font-face { font-family: "Site Sans"; src: url("../fonts/source-sans-3-400.woff2") format("woff2"); font-weight: 400; font-display: swap; }
@font-face { font-family: "Site Sans"; src: url("../fonts/source-sans-3-600.woff2") format("woff2"); font-weight: 600; font-display: swap; }

:root {
  --accent: #1a2a4a;
  --accent-soft: #33456b;
  --bg: #fbfaf7;
  --surface: #ffffff;
  --text: #1c1c1a;
  --muted: #5f5e5a;
  --line: #e6e3dc;
  --max: 720px;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font-family: "Site Sans", system-ui, sans-serif; font-size: 17px; line-height: 1.65;
}
h1, h2, h3 { font-family: "Site Serif", Georgia, serif; color: var(--accent); line-height: 1.25; }
h1 { font-size: 2rem; margin: 0.2rem 0; }
h2 { font-size: 1.5rem; }
h3 { font-size: 1.15rem; }
a { color: var(--accent-soft); text-decoration: none; }
a:hover { text-decoration: underline; }
.muted { color: var(--muted); }

/* Sticky nav */
#site-header {
  position: sticky; top: 0; z-index: 10;
  background: rgba(251, 250, 247, 0.92); backdrop-filter: blur(6px);
  border-bottom: 1px solid var(--line);
}
#site-nav {
  display: flex; justify-content: space-between; align-items: center;
  gap: 1rem; max-width: var(--max); margin: 0 auto; padding: 0.75rem 1rem;
}
.nav-name { font-family: "Site Serif", serif; font-weight: 600; font-size: 1.1rem; color: var(--accent); }
.nav-links { display: flex; flex-wrap: wrap; gap: 1rem; list-style: none; margin: 0; padding: 0; }
.nav-links a { color: var(--muted); font-size: 0.95rem; }
.nav-links a.active { color: var(--accent); border-bottom: 2px solid var(--accent); }

main { max-width: var(--max); margin: 0 auto; padding: 0 1rem; }
section { padding: 2.5rem 0; border-top: 1px solid var(--line); scroll-margin-top: 4rem; }
#hero { border-top: none; text-align: center; padding-top: 2.5rem; }

#hero-photo {
  width: 150px; height: 150px; border-radius: 50%; object-fit: cover;
  border: 3px solid var(--surface); box-shadow: 0 0 0 1px var(--line); margin-bottom: 1rem;
  background: var(--line);
}
#hero-title { font-size: 1.1rem; color: var(--muted); margin: 0.2rem 0; }
#hero-tagline { font-size: 1.15rem; max-width: 40ch; margin: 0.6rem auto 1.2rem; }
.hero-actions { margin: 1rem 0; }
.button {
  display: inline-block; background: var(--accent); color: #fff;
  padding: 0.55rem 1.1rem; border-radius: 6px; font-weight: 600;
}
.button:hover { background: var(--accent-soft); text-decoration: none; }
.icon-links { display: flex; justify-content: center; flex-wrap: wrap; gap: 1rem; list-style: none; padding: 0; margin: 1rem 0 0; }

#education-list { list-style: none; padding: 0; }
#education-list li { padding: 0.3rem 0; }
.research-item { margin-bottom: 1.2rem; }
.research-item h3 { margin: 0 0 0.2rem; }
.research-item p { margin: 0; }

/* Publications */
.pub-year { border-bottom: 1px solid var(--line); padding-bottom: 0.3rem; margin: 1.5rem 0 0.8rem; }
.pub-list { list-style: none; padding: 0; margin: 0; }
.pub-item { margin-bottom: 1.1rem; }
.pub-title { font-weight: 600; }
.pub-authors { color: var(--text); font-size: 0.95rem; }
.pub-venue { color: var(--muted); font-style: italic; font-size: 0.95rem; }
.pub-doi { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }

#contact-list { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 1rem; }
#site-footer { max-width: var(--max); margin: 0 auto; padding: 2rem 1rem; color: var(--muted); font-size: 0.9rem; border-top: 1px solid var(--line); }

@media (max-width: 600px) {
  body { font-size: 16px; }
  #site-nav { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
  .nav-links { gap: 0.75rem; }
  h1 { font-size: 1.6rem; }
}
```

- [ ] **Step 3: Verify the design at desktop and mobile widths**

Serve and navigate to `http://localhost:8000`. Use `resize_window` preset `desktop`, take a `screenshot`; then preset `mobile`, take another `screenshot`.
Expected: serif navy headings, sans body, sticky translucent nav, centered circular headshot placeholder, navy "Download CV" button, publications grouped under underlined year headings, hairline dividers between sections, single centered column. On mobile the nav stacks and text remains readable with no horizontal scroll.

- [ ] **Step 4: Commit**

```bash
git add css/style.css fonts/
git commit -m "feat: classic academic visual design with self-hosted fonts"
```

---

## Task 7: Sticky-nav active-section highlighting

**Files:**
- Modify: `js/main.js`

**Interfaces:**
- Consumes: `#site-nav .nav-links a` anchors and the `section[id]` elements.
- Produces: `initNav()` that highlights the nav link of the section currently in view (toggling the `.active` class), using `IntersectionObserver`. `init()` calls it last.

- [ ] **Step 1: Add nav behavior to main.js**

In `js/main.js`, add above `init()`:

```js
function initNav() {
  const links = new Map(
    [...document.querySelectorAll("#site-nav .nav-links a")].map((a) => [
      a.getAttribute("href").slice(1), a,
    ])
  );
  const sections = [...document.querySelectorAll("main section[id]")];
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const link = links.get(entry.target.id);
        if (!link) continue;
        if (entry.isIntersecting) {
          links.forEach((l) => l.classList.remove("active"));
          link.classList.add("active");
        }
      }
    },
    { rootMargin: "-45% 0px -45% 0px", threshold: 0 }
  );
  sections.forEach((s) => observer.observe(s));
}
```

- [ ] **Step 2: Call initNav() from init()**

In `js/main.js`, replace the `// Task 7 will initialize nav behavior here.` comment with:

```js
    initNav();
```

- [ ] **Step 3: Verify active highlighting in the browser**

Serve and navigate to `http://localhost:8000`. Use `read_page` to confirm no errors, then `scroll` down to the Publications section and `screenshot`.
Expected: as each section scrolls into the middle of the viewport, its nav link gains the navy underline (`.active`). No console errors.

- [ ] **Step 4: Commit**

```bash
git add js/main.js
git commit -m "feat: highlight active nav section on scroll"
```

---

## Task 8: Publications auto-sync GitHub Action

**Files:**
- Create: `.github/workflows/update-publications.yml`

**Interfaces:**
- Consumes: `scripts/sync_orcid.py`, `data/content.yml` (for the ORCID iD), `data/publications.json` (commit target).
- Produces: a workflow triggered weekly and manually that runs the sync and commits any change.

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/update-publications.yml`:

```yaml
name: Update publications from ORCID

on:
  schedule:
    - cron: "0 6 * * 1"      # 06:00 UTC every Monday
  workflow_dispatch: {}       # manual "Run workflow" button

permissions:
  contents: write

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Fetch ORCID and update publications.json
        run: python scripts/sync_orcid.py

      - name: Commit changes if any
        run: |
          if [[ -n "$(git status --porcelain data/publications.json)" ]]; then
            git config user.name "github-actions[bot]"
            git config user.email "github-actions[bot]@users.noreply.github.com"
            git add data/publications.json
            git commit -m "chore: refresh publications from ORCID"
            git push
          else
            echo "No publication changes."
          fi
```

Note: the script is standard-library only, so no `pip install` step is needed. It reads the ORCID iD from `data/content.yml`.

- [ ] **Step 2: Validate the workflow YAML locally**

```powershell
$PY = "C:\Users\saran\anaconda3\envs\current_env\python.exe"
& $PY -c "import json,urllib.request; import sys; sys.exit(0)"  # sanity: interpreter works
& $PY -c "import ast; print('yaml file present:', __import__('pathlib').Path('.github/workflows/update-publications.yml').exists())"
```

Expected: prints `yaml file present: True`. (A full CI run is verified after deployment in Task 9 by triggering the workflow from the GitHub UI.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/update-publications.yml
git commit -m "ci: weekly ORCID publications sync workflow"
```

---

## Task 9: Deployment scaffolding and documentation

**Files:**
- Create: `.nojekyll`
- Create: `CNAME`
- Create: `assets/headshot.jpg` (placeholder)
- Create: `assets/cv.pdf` (placeholder)
- Create: `README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: a deployable repository and author-facing docs. No code interfaces.

- [ ] **Step 1: Create Pages control files and asset placeholders**

```powershell
New-Item -ItemType File -Force .nojekyll | Out-Null
"yourdomain.com" | Out-File -Encoding ascii -NoNewline CNAME
New-Item -ItemType Directory -Force assets | Out-Null
# 1x1 placeholder headshot (author replaces with a real photo)
$png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
[IO.File]::WriteAllBytes("assets/headshot.jpg", [Convert]::FromBase64String($png))
# Minimal valid placeholder PDF (author replaces with real CV)
$pdf = "%PDF-1.1`n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj`n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj`n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj`nxref`n0 4`n0000000000 65535 f `ntrailer<</Root 1 0 R/Size 4>>`nstartxref`n0`n%%EOF"
[IO.File]::WriteAllText("assets/cv.pdf", $pdf)
```

Expected: `.nojekyll`, `CNAME`, `assets/headshot.jpg`, and `assets/cv.pdf` exist. These are placeholders the author replaces.

- [ ] **Step 2: Write the README**

Create `README.md`:

````markdown
# Personal website

A single-page academic site. Publications update automatically from ORCID.

## Edit your content

Everything you write lives in `data/content.yml`. Edit it, save, and refresh the
page. Replace these two files with your own:

- `assets/headshot.jpg` — your photo (square works best)
- `assets/cv.pdf` — your CV

Set your `orcid_id` and `scholar_url` in the `meta:` block of `data/content.yml`.
Do **not** edit `data/publications.json` — it is generated from ORCID.

## Preview locally

```powershell
& "C:\Users\saran\anaconda3\envs\current_env\python.exe" -m http.server 8000
```

Then open http://localhost:8000.

## Refresh publications manually

```powershell
& "C:\Users\saran\anaconda3\envs\current_env\python.exe" scripts/sync_orcid.py
```

This rewrites `data/publications.json` from your ORCID record. It also runs
automatically every Monday via GitHub Actions
(`.github/workflows/update-publications.yml`), and you can trigger it anytime
from the repo's **Actions** tab → "Update publications from ORCID" → "Run
workflow".

## Deploy (GitHub Pages + custom domain)

1. Create a GitHub repository and push this project to it.
2. Repo **Settings → Pages**: set "Source" to "Deploy from a branch", branch
   `main`, folder `/ (root)`.
3. Custom domain: edit `CNAME` to your domain (e.g. `yourname.com`). At your DNS
   registrar add either an `ALIAS`/`ANAME` at the apex to `USERNAME.github.io`,
   or four `A` records to GitHub Pages IPs:
   `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`.
   For a `www` subdomain add a `CNAME` record pointing to `USERNAME.github.io`.
4. Back in **Settings → Pages**, enter the same domain and enable
   "Enforce HTTPS" once the certificate provisions.

## Run tests

```powershell
& "C:\Users\saran\anaconda3\envs\current_env\python.exe" -m pytest tests/ -v
```
````

- [ ] **Step 3: Final full verification**

Run the test suite and serve the site once more.

```powershell
$PY = "C:\Users\saran\anaconda3\envs\current_env\python.exe"
& $PY -m pytest tests/ -v
Start-Process -NoNewWindow $PY -ArgumentList "-m","http.server","8000"
```

Navigate to `http://localhost:8000`, `get_page_text`, and take desktop + mobile screenshots.
Expected: all 10 tests PASS; the page renders every section with placeholder content, publications grouped by year, classic-academic styling, working nav highlighting, and no console errors.

- [ ] **Step 4: Commit**

```bash
git add .nojekyll CNAME assets/ README.md
git commit -m "docs: deployment scaffolding, placeholders, and README"
```

---

## Author-supplied content (after implementation)

The site ships fully working with placeholders. To make it yours, provide:

- Your **ORCID iD** and **Google Scholar URL** in `data/content.yml` (`meta:`).
- Your **About / Research / Teaching / Awards** text and **education** history in `data/content.yml`.
- **Email** and profile **links** in `data/content.yml` (`meta.links`).
- `assets/headshot.jpg` (your photo) and `assets/cv.pdf` (your CV).
- Your **custom domain** in `CNAME`, plus the DNS records from the README.

Then run the sync once (`python scripts/sync_orcid.py`) to populate real publications, commit, and push.

---

## Self-Review

**Spec coverage** (spec sections → tasks):

- §2 sections (Hero, About, Research, Publications, Teaching, Awards, Contact) → Tasks 1, 2, 5.
- §2 headshot + CV button → Tasks 1, 2 (wiring), 6 (style), 9 (placeholders).
- §2 auto publications from ORCID, weekly + manual → Tasks 3, 4, 8.
- §2 Scholar link (not scraped) → Task 2 (`#scholar-link`), Task 5.
- §3 dependency-free static site, no local toolchain beyond Python → whole plan; sync is stdlib-only (Global Constraints, Task 4).
- §4 repo structure → matches File Structure section.
- §6 content.yml model + browser-side YAML parse → Task 2.
- §7 fail-safe sync, ORCID public API, atomic write → Task 4; Action → Task 8.
- §8 classic academic style, navy accent, responsive, self-hosted fonts → Task 6.
- §9 GitHub Pages + custom domain + README → Tasks 8, 9.
- §10 author-supplied placeholders → shipped in Tasks 2, 9; documented above.

No gaps found.

**Placeholder scan:** No "TBD/TODO/handle edge cases" left as instructions; every code step contains complete code. Asset placeholders in Task 9 are deliberate, generated by explicit commands.

**Type consistency:** Publication dict keys (`title, venue, year, type, doi, url, put_code, authors`) are consistent between `parse_work_summary` (Task 3), `build_publications` (Task 4), and `renderPublications` (Task 5). `read_orcid_id`, `extract_doi`, `parse_contributors`, `fetch_json`/`opener`, `write_publications_atomic` signatures match between their defining tasks and their tests. DOM IDs produced in Task 1 match those consumed in Tasks 2 and 5.
