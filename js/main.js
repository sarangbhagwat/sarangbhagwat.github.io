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

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  for (const c of [].concat(children)) node.append(c);
  return node;
}

function renderContent(data) {
  const m = data.meta || {};
  document.title = [m.name, m.title].filter(Boolean).join(" — ") || "Personal website";
  document.querySelector(".nav-name").textContent = m.name || "";
  document.getElementById("hero-name").textContent = m.name || "";
  document.getElementById("hero-title").textContent =
    [m.title, m.institution].filter(Boolean).join(", ");
  document.getElementById("hero-tagline").textContent = m.tagline || "";
  document.getElementById("hero-photo").alt = m.name || "";

  const cv = document.getElementById("hero-cv");
  cv.href = "assets/cv.pdf";
  cv.setAttribute("download", "");

  const heroLinks = document.getElementById("hero-links");
  heroLinks.replaceChildren(
    ...(m.links || []).map((l) =>
      el("li", {}, el("a", { href: safeUrl(l.url), textContent: l.label }))
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
  if (m.scholar_url) scholar.href = safeUrl(m.scholar_url);

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
      el("li", {}, el("a", { href: safeUrl(l.url), textContent: l.label }))
    )
  );

  document.getElementById("footer-year").textContent = new Date().getFullYear();
  document.getElementById("footer-name").textContent = m.name || "";
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
  const hasLast = a.includes(last);
  const hasFirst = a.some((t) => t === first || t === first[0]);
  return hasLast && hasFirst;
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

async function init() {
  try {
    const data = await loadContent();
    renderContent(data);
    try {
      const pubs = await loadPublications();
      renderPublications(pubs, (data.meta || {}).name);
    } catch (pubErr) {
      console.error(pubErr);
      renderPublications({ publications: [] }, (data.meta || {}).name);
    }
    initNav();
  } catch (err) {
    console.error(err);
  }
}

document.addEventListener("DOMContentLoaded", init);
