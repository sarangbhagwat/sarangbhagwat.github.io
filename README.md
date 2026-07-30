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
