import "./vendor/js-yaml.min.js"; // exposes global `jsyaml`

function safeUrl(url) {
  const u = (url == null ? "" : String(url)).trim();
  if (!u) return "#";
  if (/^(https?:|mailto:)/i.test(u)) return u;   // safe absolute schemes
  if (/^[a-z][a-z0-9+.-]*:/i.test(u)) return "#"; // any other explicit scheme -> block
  return u;                                        // relative URL (no scheme) -> safe
}

async function loadContent() {
  const res = await fetch("data/content.yml", { cache: "no-cache" });
  if (!res.ok) throw new Error(`content.yml HTTP ${res.status}`);
  const text = await res.text();
  return window.jsyaml.load(text);
}

async function loadSoftware() {
  try {
    const res = await fetch("data/software.json", { cache: "no-cache" });
    if (res.ok) return res.json();
  } catch (e) {
    console.error(e);
  }
  return { repos: {}, packages: {} };
}

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  for (const c of [].concat(children)) node.append(c);
  return node;
}

// Parses trusted, static inline SVG markup (authored below, never user/network data)
// into a real SVGElement — <template> parsing switches to foreign-content mode for
// <svg>, giving proper namespacing without manual createElementNS calls per node.
function svgIcon(inner) {
  const tpl = document.createElement("template");
  tpl.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true" focusable="false">${inner}</svg>`;
  return tpl.content.firstChild;
}

const moonIcon = () => svgIcon('<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>');
const sunIcon = () => svgIcon(
  '<circle cx="12" cy="12" r="4.3" fill="none" stroke="currentColor" stroke-width="1.6"/>' +
  '<g stroke="currentColor" stroke-width="1.6" stroke-linecap="round">' +
  '<line x1="12" y1="2.6" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="21.4"/>' +
  '<line x1="2.6" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="21.4" y2="12"/>' +
  '<line x1="4.9" y1="4.9" x2="6.6" y2="6.6"/><line x1="17.4" y1="17.4" x2="19.1" y2="19.1"/>' +
  '<line x1="4.9" y1="19.1" x2="6.6" y2="17.4"/><line x1="17.4" y1="6.6" x2="19.1" y2="4.9"/></g>'
);

// Monochrome, currentColor icons keyed by normalized (lowercased) link label.
const ICONS = {
  "google scholar": () => svgIcon(
    '<path d="M12 3 1 9l11 6 11-6-11-6Z"/>' +
    '<path d="M5 11.5v4.8c0 1.7 3.1 3.2 7 3.2s7-1.5 7-3.2v-4.8l-7 3.8-7-3.8Z"/>'
  ),
  orcid: () => svgIcon(
    '<circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" stroke-width="1.5"/>' +
    '<circle cx="8.3" cy="8.2" r="1.1"/>' +
    '<g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">' +
    '<line x1="8.3" y1="10.6" x2="8.3" y2="16.4"/>' +
    '<line x1="11.8" y1="10.6" x2="15.6" y2="10.6"/>' +
    '<line x1="11.8" y1="13.3" x2="15.6" y2="13.3"/>' +
    '<line x1="11.8" y1="16" x2="14.2" y2="16"/></g>'
  ),
  email: () => svgIcon(
    '<rect x="2.5" y="5" width="19" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/>' +
    '<path d="M3.5 6.5 12 13 20.5 6.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
  ),
  github: () => svgIcon(
    '<path d="M12 2C6.48 2 2 6.58 2 12.26c0 4.54 2.87 8.38 6.84 9.74.5.1.68-.22.68-.49 ' +
    '0-.24-.01-1.04-.01-1.89-2.78.62-3.37-1.19-3.37-1.19-.46-1.18-1.11-1.5-1.11-1.5-.91-.63.07-.62.07-.62 ' +
    '1 .07 1.53 1.05 1.53 1.05.89 1.56 2.34 1.11 2.91.85.09-.66.35-1.11.63-1.37-2.22-.26-4.56-1.14-4.56-5.06 ' +
    '0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.71 0 0 .84-.28 2.75 1.05a9.3 9.3 0 0 1 5 0c1.91-1.33 2.75-1.05 ' +
    '2.75-1.05.55 1.41.2 2.45.1 2.71.64.72 1.03 1.63 1.03 2.75 0 3.93-2.34 4.79-4.57 5.05.36.32.68.95.68 1.92 ' +
    '0 1.39-.01 2.51-.01 2.85 0 .27.18.6.69.49A10.02 10.02 0 0 0 22 12.26C22 6.58 17.52 2 12 2Z"/>'
  ),
  linkedin: () => svgIcon(
    '<rect x="2.5" y="2.5" width="19" height="19" rx="4" fill="none" stroke="currentColor" stroke-width="1.6"/>' +
    '<circle cx="7" cy="7.5" r="1.35"/>' +
    // "in" drawn as even-weight strokes so the i-stem and both n legs match.
    '<path d="M7 17.9V10.2" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>' +
    '<path d="M11.4 17.9V13a3 3 0 0 1 6 0v4.9" fill="none" stroke="currentColor" ' +
    'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
  ),
};

// Looks up an icon by case-insensitive label, falling back to the mailto: scheme
// (contact's email link uses the address itself as its label, not "Email").
function iconFor(label, url) {
  const byLabel = ICONS[(label || "").trim().toLowerCase()];
  if (byLabel) return byLabel();
  if (/^mailto:/i.test((url || "").trim())) return ICONS.email();
  return null;
}

// Shared anchor builder for hero links and the contact link: icon (if known) + label.
// The visible label remains the accessible name, so the icon stays aria-hidden.
function iconLink(label, url) {
  const a = el("a", { className: "icon-link", href: safeUrl(url) });
  const icon = iconFor(label, url);
  if (icon) a.append(icon);
  a.append(label);
  return el("li", {}, a);
}

function richText(text) {
  // Renders markdown-style links [label](url) as anchors; everything else as plain text.
  const frag = document.createDocumentFragment();
  const s = String(text == null ? "" : text);
  const re = /\[([^\]]+)\]\(([^)\s]+)\)/g;
  let last = 0, match;
  while ((match = re.exec(s)) !== null) {
    if (match.index > last) frag.append(s.slice(last, match.index));
    frag.append(el("a", { href: safeUrl(match[2]), textContent: match[1] }));
    last = match.index + match[0].length;
  }
  if (last < s.length) frag.append(s.slice(last));
  return frag;
}

function fill(id, nodes) {
  const target = document.getElementById(id);
  if (target) target.replaceChildren(...nodes);
}

function show(id, visible) {
  const target = document.getElementById(id);
  if (target) target.hidden = !visible;
  const navLink = document.querySelector(`#site-nav .nav-links a[href="#${id}"]`);
  if (navLink) navLink.parentElement.hidden = !visible;
}

// Full display name assembled from the structured name parts in content.yml.
// Middle is optional and rendered as written — a full name or an initial ("S.").
function fullName(meta) {
  return [meta.first_name, meta.middle_name, meta.last_name]
    .filter(Boolean).join(" ").trim();
}

// Paints alternating full-bleed bands on the visible sections (skipping the
// hero). Computed over :not([hidden]) so sections hidden for lack of content
// (teaching/awards) don't break the cream/white alternation. The first visible
// section after the hero gets the white band, so About pops against the hero.
function assignBands() {
  const sections = [...document.querySelectorAll("main section:not([hidden])")]
    .filter((s) => s.id !== "hero" && s.id !== "news");
  sections.forEach((s, i) => s.classList.toggle("section-alt", i % 2 === 0));
}

// Renders the Software cards, merging live metrics (stars, monthly downloads)
// keyed by the entry's repo slug and pypi name. Missing metrics are simply
// omitted — the card still renders from the editorial content.
function renderSoftware(software, metrics) {
  const list = software || [];
  const repos = (metrics && metrics.repos) || {};
  const packages = (metrics && metrics.packages) || {};
  const cards = list.map((s) => {
    const card = el("div", { className: "software-card" });
    const head = el("div", { className: "software-head" });
    head.append(el("h3", { className: "software-name", textContent: s.name || "" }));
    if (s.role) head.append(el("span", { className: "software-role", textContent: s.role }));
    card.append(head);
    if (s.description) card.append(el("p", { className: "software-desc" }, richText(s.description)));

    const repoM = s.repo ? repos[s.repo] : null;
    const pkgM = s.pypi ? packages[s.pypi] : null;
    const stats = [];
    if (repoM && typeof repoM.stars === "number" && repoM.stars > 0) {
      stats.push(`★ ${repoM.stars.toLocaleString()} stars`);
    }
    if (pkgM && typeof pkgM.last_month === "number" && pkgM.last_month > 0) {
      stats.push(`${pkgM.last_month.toLocaleString()} downloads/mo`);
    }
    if (stats.length) {
      card.append(el("div", { className: "software-stats", textContent: stats.join("  ·  ") }));
    }

    const links = [];
    if (s.repo) links.push(el("a", { className: "software-link", href: safeUrl(`https://github.com/${s.repo}`), textContent: "GitHub" }));
    if (s.url) links.push(el("a", { className: "software-link", href: safeUrl(s.url), textContent: "Docs / site" }));
    if (links.length) {
      const wrap = el("div", { className: "software-links" });
      links.forEach((a, i) => { if (i) wrap.append(document.createTextNode(" ")); wrap.append(a); });
      card.append(wrap);
    }
    return card;
  });
  fill("software-list", cards);
  show("software", list.length > 0);
}

// Compact dated updates shown as a strip below the hero. Each item is
// "date — text", with markdown links in the text supported via richText().
function renderNews(news) {
  const list = news || [];
  fill("news-list", list.map((n) => {
    const li = el("li", { className: "news-item" });
    if (n.date) li.append(el("span", { className: "news-date", textContent: String(n.date) }));
    li.append(el("span", { className: "news-text" }, richText(n.text || "")));
    return li;
  }));
  show("news", list.length > 0);
}

function renderContent(data, softwareMetrics) {
  const m = data.meta || {};
  renderNews(data.news || []);
  const name = fullName(m);
  document.title = name || "Personal website";
  document.querySelector(".nav-name").textContent = name;
  document.getElementById("hero-name").textContent = name;
  document.getElementById("hero-title").textContent =
    [m.title, m.institution].filter(Boolean).join(", ");
  document.getElementById("hero-tagline").textContent = m.tagline || "";
  document.getElementById("hero-photo").alt = name;

  const heroLinks = document.getElementById("hero-links");
  heroLinks.replaceChildren(...(m.links || []).map((l) => iconLink(l.label, l.url)));

  const about = data.about || [];
  const education = data.education || [];
  fill("about-body", about.map((p) => el("p", {}, richText(p))));
  fill("education-list", education.map((e) => {
    const li = el("li", { className: "edu-item" });
    li.append(el("span", { className: "edu-year", textContent: String(e.year || "") }));
    li.append(el("div", { className: "edu-degree", textContent: e.degree || "" }));
    li.append(el("div", { className: "edu-inst", textContent: e.institution || "" }));
    return li;
  }));
  show("about", about.length > 0);
  show("education", education.length > 0);
  const heroGrid = document.querySelector(".hero-grid");
  if (heroGrid) heroGrid.classList.toggle("has-education", education.length > 0);

  const vision = data.research_vision || [];
  fill("research-vision", vision.map((v) => {
    const item = el("div", { className: "vision-item" });
    if (v.heading) item.append(el("h3", { className: "vision-heading", textContent: v.heading }));
    if (v.body) item.append(el("p", { className: "vision-body" }, richText(v.body)));
    return item;
  }));

  const research = data.research_interests || [];
  const leads = research.filter((r) => r.heading);
  const bodies = research.filter((r) => r.body);
  const researchNodes = [];
  for (const r of leads) {
    researchNodes.push(el("p", {
      className: "research-lead",
      textContent: String(r.heading).split(";").map((s) => s.trim()).filter(Boolean).join(" · "),
    }));
  }
  if (bodies.length) {
    researchNodes.push(el("ul", { className: "research-list" },
      bodies.map((r) => el("li", {}, richText(r.body)))));
  }
  fill("research-list", researchNodes);
  show("research", research.length > 0 || vision.length > 0);

  const scholar = document.getElementById("scholar-link");
  if (scholar && m.scholar_url) scholar.href = safeUrl(m.scholar_url);

  const teaching = data.teaching || {};
  const courses = teaching.courses || [];
  fill("teaching-philosophy",
    teaching.philosophy ? [el("p", {}, richText(teaching.philosophy))] : []);
  fill("teaching-courses", courses.map((c) => el("li", { textContent: c })));
  show("teaching", Boolean(teaching.philosophy) || courses.length > 0);
  show("courses-heading", courses.length > 0);

  const awards = data.awards || [];
  fill("awards-list", awards.map((a) =>
    el("li", {}, [el("strong", { textContent: `${a.year} ` }), richText(a.description)])
  ));
  show("awards", awards.length > 0);

  const email = (m.email || "").trim();
  fill("contact-list", email ? [iconLink(email, `mailto:${email}`)] : []);
  show("contact", Boolean(email));

  document.getElementById("footer-year").textContent = new Date().getFullYear();
  document.getElementById("footer-name").textContent = name;

  renderSoftware(data.software || [], softwareMetrics || { repos: {}, packages: {} });

  assignBands();
}

async function loadPublications() {
  const res = await fetch("data/publications.json", { cache: "no-cache" });
  if (!res.ok) throw new Error(`publications.json HTTP ${res.status}`);
  return res.json();
}

function isSelfAuthor(name, selfName) {
  if (!name || !selfName) return false;
  const toks = (s) => s.toLowerCase().replace(/[.,]/g, " ").split(/\s+/).filter(Boolean);
  const a = toks(name), self = toks(selfName);
  if (a.length < 1 || self.length < 2) return false;
  const first = self[0], last = self[self.length - 1];
  if (!a.includes(last)) return false;
  // Only the primary given name decides: a full name must match exactly;
  // a bare initial may match the first initial. Middle initials never count.
  const given = a.filter((t) => t !== last);
  if (given.length === 0) return false;
  const g = given[0];
  return g === first || (g.length === 1 && g === first[0]);
}

function authorsFragment(authors, selfName) {
  const frag = document.createDocumentFragment();
  authors.forEach((name, i) => {
    if (i > 0) frag.append(", ");
    const isSelf = isSelfAuthor(name, selfName);
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
  let num = pubs.length; // reverse numbering: oldest = 1, newest = highest
  for (const y of years) {
    blocks.push(el("h3", { className: "pub-year", textContent: String(y) }));
    const items = byYear.get(y).map((p) => {
      const li = el("li", { className: "pub-item" });
      li.append(el("span", { className: "pub-num", textContent: `${num--}.` }));
      li.append(el("span", { className: "pub-title", textContent: p.title || "Untitled" }));
      if (p.authors && p.authors.length) {
        li.append(el("div", { className: "pub-authors" }, authorsFragment(p.authors, selfName)));
      }
      const meta = [p.venue, p.year].filter(Boolean).join(", ");
      if (meta) li.append(el("div", { className: "pub-venue", textContent: meta }));
      if (p.url) li.append(el("a", { className: "pub-doi", href: safeUrl(p.url), textContent: "DOI" }));
      return li;
    });
    blocks.push(el("ul", { className: "pub-list" }, items));
  }
  list.replaceChildren(...blocks);
}

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

// Fade/rise-in as sections scroll into view. Gated behind .js-reveal (added
// here, before observing) so no-JS users get the default, fully-visible CSS.
function initReveal() {
  const sections = [...document.querySelectorAll("main section[id]")];
  const observer = new IntersectionObserver(
    (entries, obs) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("revealed");
        obs.unobserve(entry.target);
      }
    },
    { threshold: 0.1 }
  );
  document.documentElement.classList.add("js-reveal");
  sections.forEach((s) => observer.observe(s));
}

// Light/dark toggle. The pre-paint script in index.html has already set
// data-theme; here we render the button to match, flip it on click (saving the
// choice), and keep following the OS while no explicit choice is saved.
function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function updateToggle(btn) {
  const goingDark = currentTheme() === "light";
  const label = goingDark ? "Switch to dark mode" : "Switch to light mode";
  btn.replaceChildren(goingDark ? moonIcon() : sunIcon());
  btn.setAttribute("aria-label", label);
  btn.title = label;
}

function initThemeToggle() {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  updateToggle(btn);
  btn.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) { /* ignore */ }
    updateToggle(btn);
  });
  // Follow the OS while the visitor hasn't made an explicit choice.
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    let saved = null;
    try { saved = localStorage.getItem("theme"); } catch (_) { /* ignore */ }
    if (saved) return;
    document.documentElement.dataset.theme = e.matches ? "dark" : "light";
    updateToggle(btn);
  });
}

// Points the CV button at the file detected by scripts/detect_cv.py (recorded
// in data/cv.json), so the PDF can be renamed without editing any code. Hides
// the button if no CV is found, rather than linking to a 404.
async function initCvButton() {
  const cv = document.getElementById("hero-cv");
  if (!cv) return;
  let path = null;
  try {
    const res = await fetch("data/cv.json", { cache: "no-cache" });
    if (res.ok) {
      const doc = await res.json();
      path = doc && doc.file ? doc.file : null;
    }
  } catch (e) {
    console.error(e);
  }
  if (path) {
    cv.href = safeUrl(path);
    cv.setAttribute("download", "");
    cv.hidden = false;
  } else {
    cv.hidden = true;
  }
}

async function init() {
  try {
    initReveal(); // sync, before the content fetch: hero reveals immediately
  } catch (e) {
    console.error(e);
  }
  try {
    initThemeToggle();
  } catch (e) {
    console.error(e);
  }
  initCvButton(); // async + self-contained: independent of content/publications
  try {
    const data = await loadContent();
    let softwareMetrics = { repos: {}, packages: {} };
    try {
      softwareMetrics = await loadSoftware();
    } catch (e) {
      console.error(e);
    }
    renderContent(data, softwareMetrics);
    const selfName = fullName(data.meta || {});
    try {
      const pubs = await loadPublications();
      renderPublications(pubs, selfName);
    } catch (pubErr) {
      console.error(pubErr);
      renderPublications({ publications: [] }, selfName);
    }
    initNav();
  } catch (err) {
    console.error(err);
  }
}

document.addEventListener("DOMContentLoaded", init);
