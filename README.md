# Personal website

A single-page academic site. Publications update automatically from ORCID.

## Edit your content

Everything you write lives in `data/content.yml`. Edit it, save, and refresh the
page. Replace these two files with your own:

- `assets/headshot.jpg` — your photo (square works best)
- `assets/<last>-<first>_CV*.pdf` — your CV. The site builds the expected
  prefix from your name in `content.yml`, so with `first_name: "Sarang"` and
  `last_name: "Bhagwat"` it looks for files starting with `Bhagwat-Sarang_CV`
  (e.g. add a date suffix like `Bhagwat-Sarang_CV_2026-07.pdf`); if several
  match, the highest-sorting name wins. The link is wired up from
  `data/cv.json`, which `scripts/detect_cv.py` regenerates in CI whenever
  `assets/` or `content.yml` changes — do not edit it by hand.

The page title and meta description in `index.html` are generated too.
`scripts/sync_head.py` builds them from your name, title, and institution in
`content.yml` and rewrites those two tags in place, so do not edit them by
hand. CI runs it whenever `content.yml` changes; run
`python scripts/sync_head.py` yourself if you want them updated before you
push.

Your name goes in the `meta:` block of `data/content.yml` as `first_name`,
`middle_name` (optional), and `last_name`. Everything that shows your name —
the page, the title, the CV filename — is built from those parts. Also set your
`orcid_id` and `scholar_url` there. Do **not** edit `data/publications.json` —
it is generated from ORCID.
