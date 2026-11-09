"""Shared helpers for build_site.py: text clean-up, page frame, images, icons and ornaments.

Kept compatible with Python 3.10 (no backslashes or reused quotes inside f-string expressions).
"""
import html
import json
import math
import pathlib
import re
import sys
import unicodedata

import markdown

H = html.escape
HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
DOCS = SITE / "docs"
FAMILY = pathlib.Path(sys.argv[sys.argv.index("--family") + 1]) if "--family" in sys.argv else SITE.parent
DATA = HERE / "data"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


CFG = load("config.json")
SITE_TITLE = "The Rodilitz and Zaslow Families"
BASE_URL = "https://" + CFG["cname"].strip() + "/" if CFG.get("cname") else ""
ERRORS = []


def error(msg):
    ERRORS.append(msg)
    print("ERROR:", msg)


# ----------------------------------------------------------------------------------------------
# text
# ----------------------------------------------------------------------------------------------

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def md(text, inline=False):
    out = markdown.markdown(text, extensions=["tables", "sane_lists", "attr_list"])
    if inline:
        out = re.sub(r"^<p>(.*)</p>$", r"\1", out.strip(), flags=re.S)
    return out


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def shorten(s, n=155):
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


# Publication scrub for the working research files: internal task references, the research assistant, private notes.
SCRUB = [
    (r"\s*\((?:[^()]*?\b(?:RZ-T\d+|coordinator|Claude|agents?|Sonnet|Opus)\b[^()]*)\)", ""),
    (r";\s*(?:coordinator|Claude)[^;)]*", ""),
    (r"\b(?:Corrected|corrected|confirmed|Confirmed|found|read|checked) by RZ-T\d+", lambda m: m.group(0).split(" by ")[0] + " in later research"),
    (r"\bby RZ-T\d+\b", "in later research"),
    (r"\bthe agent[’']s\b", "the research’s"),
    (r"\b[Tt]he agents?\b", "the research"),
    (r"\b(?:RZ-T\d+(?:\s*(?:to|–|-|and|,)\s*RZ-T\d+)*)\s*(?:report|reports)?\b", "the research"),
    (r"\bBarnst[’']s\b", "the compiler’s"),
    (r"\bBarnst\b", "the compiler"),
    (r"\bthe coordinator\b", "the research"),
    (r"\bcoordinator\b", "research"),
    (r"\bClaude\b", "the compiler"),
    (r"Mildred Finkelstein", "his first wife"),
    (r"`([^`]+)`", r"\1"),
]
SCRUB = [(re.compile(a), b) for a, b in SCRUB]
DROP_LINE = re.compile(r"Sylvia M\.? Rodilitz|Victor E\.? Koik|16 Feb 1956|dorisarchive|Agent reports/|Barnst to (?:save|send|decide)|"
                       r"needs Barnst|Barnst's (?:Chrome|JewishGen|Ancestry)", re.I)


def scrub(s):
    for rx, rep in SCRUB:
        s = rx.sub(rep, s)
    s = re.sub(r"\b(the research)(?:[,;]? the research)+", r"\1", s)
    s = re.sub(r"\(\s*(?:the research)?\s*\)", "", s)
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    s = re.sub(r"\(\s*[,;]\s*", "(", s)
    s = re.sub(r"[,;]\s*\)", ")", s)
    return s


# ----------------------------------------------------------------------------------------------
# icons and ornaments
# ----------------------------------------------------------------------------------------------

ICON_PATHS = {
    "book": '<path d="M4 5.5C6.5 4.5 9.5 4.5 12 6c2.5-1.5 5.5-1.5 8-.5V19c-2.5-1-5.5-1-8 .5-2.5-1.5-5.5-1.5-8-.5z"/><path d="M12 6v13.5"/>',
    "person": '<circle cx="12" cy="8" r="3.6"/><path d="M5 20c.8-3.8 3.6-5.8 7-5.8s6.2 2 7 5.8"/>',
    "tree": '<rect x="9" y="3" width="6" height="4.5" rx="1"/><rect x="3" y="16" width="6" height="4.5" rx="1"/><rect x="15" y="16" width="6" height="4.5" rx="1"/><path d="M12 7.5V12M6 16v-4h12v4"/>',
    "map": '<path d="M12 21s-6.5-6-6.5-11a6.5 6.5 0 0 1 13 0c0 5-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.4"/>',
    "record": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 15.5h6M9 9h3"/>',
    "question": '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.3-4.3"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8v.1"/>',
    "download": '<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14"/>',
}


def icon(name, size=22):
    return (f'<svg class="ico" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICON_PATHS[name]}</svg>')


OCHRE, RKEY, ZKEY = "#9C7430", "#8A2B1E", "#1E3F6B"


def rosette(cx, cy, r, color=OCHRE, sw=0.8):
    """Six-petal compass rosette, as on East European Jewish gravestones and papercuts (the printed history's ornament)."""
    out = []
    for k in range(6):
        a = math.radians(90 + 60 * k)
        tx, ty = cx + r * math.cos(a), cy - r * math.sin(a)
        out.append(f'<path d="M{cx:.2f},{cy:.2f} A{r:.2f},{r:.2f} 0 0 1 {tx:.2f},{ty:.2f} A{r:.2f},{r:.2f} 0 0 1 {cx:.2f},{cy:.2f} Z" '
                   f'fill="{color}" fill-opacity="{0.9 if k % 2 == 0 else 0.55}" stroke="{color}" stroke-width="{sw}"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r:.2f}" fill="none" stroke="{color}" stroke-width="{sw}"/>')
    return "".join(out)


def orn(size=14, color=OCHRE):
    return (f'<svg class="orn" viewBox="0 0 20 20" width="{size}" height="{size}" aria-hidden="true" focusable="false">'
            f'{rosette(10, 10, 8.6, color, 0.7)}</svg>')


def roundel(cls="roundel"):
    c, parts = 60, []
    parts.append(f'<circle cx="{c}" cy="{c}" r="57" fill="none" stroke="{OCHRE}" stroke-width="1"/>')
    parts.append(f'<circle cx="{c}" cy="{c}" r="52" fill="none" stroke="{OCHRE}" stroke-width="0.6"/>')
    for k in range(36):
        a = math.radians(k * 10)
        parts.append(f'<circle cx="{c + 54.5 * math.cos(a):.2f}" cy="{c + 54.5 * math.sin(a):.2f}" r="1.05" fill="{OCHRE}"/>')
    for k in range(12):
        a = math.radians(15 + k * 30)
        x1, y1 = c + 36 * math.cos(a), c + 36 * math.sin(a)
        x2, y2 = c + 47 * math.cos(a), c + 47 * math.sin(a)
        col = RKEY if k % 2 == 0 else ZKEY
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        nx, ny = -(y2 - y1) * 0.28, (x2 - x1) * 0.28
        parts.append(f'<path d="M{x1:.2f},{y1:.2f} Q{mx + nx:.2f},{my + ny:.2f} {x2:.2f},{y2:.2f} Q{mx - nx:.2f},{my - ny:.2f} {x1:.2f},{y1:.2f} Z" fill="{col}" fill-opacity="0.8"/>')
    parts.append(rosette(c, c, 30, OCHRE, 0.9))
    return f'<svg class="{cls}" viewBox="0 0 120 120" aria-hidden="true" focusable="false">{"".join(parts)}</svg>'


def divider():
    return f'<div class="divider" aria-hidden="true"><span class="rl"></span>{orn(12)}<span class="rl"></span></div>'


# ----------------------------------------------------------------------------------------------
# page frame
# ----------------------------------------------------------------------------------------------

NAV = [("history", "The story", "history/index.html"), ("people", "People", "people/index.html"),
       ("tree", "Family tree", "tree/index.html"), ("map", "Map", "map/index.html"),
       ("records", "Records", "records/index.html"), ("research", "Research", "research/index.html"),
       ("about", "About", "about/index.html")]


def page(path, title, body, active="", desc="", head="", scripts="", root=None, image=None, crumbs=None, surface=True):
    """Write one page. path is relative to docs/, e.g. 'people/r-010.html'."""
    depth = path.count("/")
    R = root if root is not None else "../" * depth
    cur = ' aria-current="page"'
    nav = "".join(f'<a href="{R}{href}"{cur if key == active else ""}>{lab}</a>' for key, lab, href in NAV)
    full_title = SITE_TITLE if title == SITE_TITLE else f"{title} · {SITE_TITLE}"
    desc = shorten(desc or CFG["site_description"], 160)
    canon = BASE_URL + ("" if path == "index.html" else path.replace("index.html", "")) if BASE_URL else ""
    og_img = (BASE_URL + image.replace("{R}", "")) if (BASE_URL and image) else ""
    meta = [f'<meta name="description" content="{H(desc)}">',
            ('' if CFG.get('allow_crawlers', False) else '<meta name="robots" content="noindex, nofollow, noarchive, noimageindex, noai, noimageai">'),
            f'<meta property="og:title" content="{H(title)}">', f'<meta property="og:description" content="{H(desc)}">',
            '<meta property="og:type" content="website">', f'<meta property="og:site_name" content="{SITE_TITLE}">',
            '<meta name="theme-color" content="#2A2219">']
    if canon:
        meta.append(f'<link rel="canonical" href="{canon}">')
        meta.append(f'<meta property="og:url" content="{canon}">')
    if og_img:
        meta.append(f'<meta property="og:image" content="{og_img}">')
    cr = ""
    if crumbs:
        cr = ('<nav class="crumbs" aria-label="Breadcrumb"><ol>' + "".join(
            f'<li><a href="{R}{u}">{H(t)}</a></li>' if u else f'<li aria-current="page">{H(t)}</li>' for t, u in crumbs) + "</ol></nav>")
    body = body.replace("{R}", R)
    if surface:
        body = f'<div class="surface">{cr}{body}</div>'
    else:
        body = (f'<div class="crumbwrap">{cr}</div>' if cr else '') + body
    out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{H(full_title)}</title>
{chr(10).join(m for m in meta if m)}
<link rel="icon" href="{R}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{R}assets/site.css">
{head.replace('{R}', R)}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="masthead"><div class="in">
<a class="brand" href="{R}index.html">{orn(26)}<span><span class="t">The Rodilitz and Zaslow Families</span><span class="s">From Grodno, Volhynia and Podolia to America</span></span></a>
<button class="navtoggle" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button>
<nav class="site-nav" id="site-nav" aria-label="Main">{nav}</nav>
</div></header>
<main id="main" tabindex="-1">
{body}
</main>
<footer class="sitefoot"><div class="in">
<div><b>{SITE_TITLE}</b><br>Compiled by {H(CFG['editor'])} · Site updated {H(CFG['site_updated'])} · Text: {H(CFG['edition'])}</div>
<div><a href="{R}about/index.html">About and credits</a> · <a href="{CFG['corrections_url']}">Send a correction</a> · <a href="{R}downloads/{CFG['pdf_download']}">Download the PDF</a></div>
</div></footer>
<script src="{R}assets/site.js"></script>
{scripts.replace('{R}', R)}
</body>
</html>
"""
    f = DOCS / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(out, encoding="utf-8")
    return path


def head_block(kicker, title, dek="", strand="sh", extra=""):
    k = f'<span class="kicker">{orn(13)}{kicker}</span>' if kicker else ""
    d = f'<p class="dek">{dek}</p>' if dek else ""
    return f'<header class="page-head {strand}">{k}<h1>{title}</h1>{d}{extra}</header>'
