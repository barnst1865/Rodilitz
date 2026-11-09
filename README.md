# The Rodilitz and Zaslow Families

A website of the family history of Theodore Rodilitz and Doris Zaslow: the Rodilitz, Hausman, Saslow and Zaslow
families, from Grodno, Volhynia and Podolia to Brooklyn and Philadelphia. It has the history chapter by chapter, a
page for every person, the records behind it, a family tree, a map and the research still in progress. It follows the
structure of the Leoke and Koik site.

The published site is the `docs/` folder, served by GitHub Pages. Everything in it is generated; don't edit it by hand.

## Folders

| Path | What it is |
|---|---|
| `docs/` | The website (HTML, images, styles). GitHub Pages publishes this folder. |
| `tools/build_site.py` | Builds every page from the family-history text and the research files. |
| `tools/sitelib.py` | Shared helpers: page frame (masthead, footer, meta tags), the rosette ornament, icons, text clean-up. |
| `tools/assets/` | Stylesheet, scripts, fonts (Frank Ruhl Libre, Source Serif 4, Source Sans 3), Leaflet, the overview tree and the printed maps (SVG, from the PDF build). |
| `tools/data/config.json` | Edition, master text, PDF, chapter summaries, links from names to people, research questions, new findings since the edition, About text, privacy redactions. |
| `tools/data/people.json` | Each person's display name, parents, spouses and short biography (drawn from the history). Dates, birthplaces, link status and sources come from `02 Family tree.md`. |
| `tools/data/chapter_people.json` | Which people appear in each chapter (the list beside each chapter). |
| `tools/data/places.json` | Places, events, routes and map views for the interactive map. |

## Rebuilding

The script expects this folder to sit inside the `Family` folder, next to `Rodilitz-Zaslow Research\`. It only reads
from there:

- `Rodilitz-Zaslow Research/PDF build/Rodilitz_Zaslow_Family_History_v2_text.md` (the master text) and `img/` (its images)
- `Rodilitz-Zaslow Research/PDF build/Rodilitz_Zaslow_Family_History_v2.pdf` (the download; living people's details are blanked)
- `Rodilitz-Zaslow Research/02 Family tree.md`, `03 Sources and citations.md` and `01 Findings.md`

```
cd Family/Rodilitz/tools
python3 build_site.py                       # or: python3 build_site.py --family PATH_TO_FAMILY_FOLDER
```

Needs Python 3 with `markdown`, `Pillow` and `pymupdf` (`pip install markdown pillow pymupdf`). The build stops with
errors if a footnote, person, source code, link or fragment does not resolve, or if private or internal text
(task codes, names of living people) would be published.

To check it locally, serve `docs/` (the tree and map load data files, which browsers block from `file://`):

```
cd Family/Rodilitz/docs
python3 -m http.server 8000      # then open http://localhost:8000
```

## A new edition of the history

1. In `tools/data/config.json`, change `master_text`, `pdf_source` and `edition`, and move the items now in the text
   out of `since_edition`.
2. If the tree or maps changed, copy the new SVGs from the PDF build to `tools/assets/tree_overview.svg` and
   `tools/assets/maps/`.
3. Add new people to `people.json` (and `02 Family tree.md`), `chapter_people.json` and `places.json`; rebuild.

## Publishing

GitHub Pages: **Settings › Pages › Build and deployment › Deploy from a branch**, branch `main`, folder `/docs`. The
site is at https://rodilitz.dckoiks.com/ (set as `"cname"` in `config.json`; the build writes `docs/CNAME`). To change the custom domain, put it in `config.json` as `"cname"`,
rebuild, push, and enter the same domain under **Settings › Pages › Custom domain**, with a `CNAME` DNS record pointing
to `barnst1865.github.io`.

## Privacy and rights

- Crawlers are asked to stay out: `robots.txt` disallows everything and every page carries a `noindex` robots tag.
- People born after 1930 who may be living have no pages; details of living people are left out of the web text and
  blanked in the downloadable PDF. The research does not record living descendants.
- Internal task references and working notes about the research process are scrubbed from the research notes.
- The record images belong to the archives credited on each page and on the About page.
