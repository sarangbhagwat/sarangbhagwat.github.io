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
  document.getElementById("hero-photo").alt = m.name || "";

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
