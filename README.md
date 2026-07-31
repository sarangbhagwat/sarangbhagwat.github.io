# Personal website

A single-page academic site. Publications update automatically from ORCID.

## Edit your content

Everything you write lives in `data/content.yml`. Edit it, save, and refresh the
page. Replace these two files with your own:

- `assets/headshot.jpg` — your photo (square works best)
- `assets/Bhagwat-Sarang_CV*.pdf` — your CV. Any file whose name starts with
  `Bhagwat-Sarang_CV` is detected automatically (e.g. add a date suffix like
  `Bhagwat-Sarang_CV_2026-07.pdf`); if several match, the highest-sorting name
  wins. The link is wired up from `data/cv.json`, which
  `scripts/detect_cv.py` regenerates in CI whenever `assets/` changes — do not
  edit it by hand.

Set your `orcid_id` and `scholar_url` in the `meta:` block of `data/content.yml`.
Do **not** edit `data/publications.json` — it is generated from ORCID.
