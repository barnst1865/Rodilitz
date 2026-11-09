"""Build the Rodilitz and Zaslow family-history website.

    python3 build_site.py [--family PATH_TO_FAMILY_FOLDER]

Reads (never changes):
  Family/Rodilitz-Zaslow Research/PDF build/<master text>.md   the family history: the single source for the narrative
  Family/Rodilitz-Zaslow Research/PDF build/img/               its illustrations (record images)
  Family/Rodilitz-Zaslow Research/02 Family tree.md            people: IDs, dates, birthplaces, link status, sources
  Family/Rodilitz-Zaslow Research/03 Sources and citations.md  every source code with its permanent link
  Family/Rodilitz-Zaslow Research/01 Findings.md               working research notes (shown folded on person pages)
  tools/data/*.json                                            config, people (relationships, biographies), places
Writes:
  docs/                                                        the published site (GitHub Pages serves this folder)

The build stops with errors if a footnote, link, person or source code does not resolve.
"""
import json
import re
import shutil
from collections import OrderedDict, defaultdict

import markdown
from PIL import Image

from sitelib import (BASE_URL, CFG, DOCS, DROP_LINE, ERRORS, FAMILY, HERE, H, SITE_TITLE, divider, error, head_block, icon, load,
                     md, orn, page, roundel, scrub, shorten, slug, strip_tags)

RP = FAMILY / CFG["research_dir"]
MASTER = (FAMILY / CFG["master_text"]).read_text(encoding="utf-8")
EDITION = CFG["edition"]
EDITION_PHRASE = EDITION.split(" · ")[0].lower() + (" (" + EDITION.split(" · ")[1] + ")" if " · " in EDITION else "")
PDF_NAME = CFG["pdf_download"]
PEOPLE_DATA = load("people.json")
CHAPTER_PEOPLE = load("chapter_people.json")
PLACES = load("places.json")
WRITTEN = []
YEAR = re.compile(r"\b(1[5-9]\d\d|20\d\d)\b")


def year_of(s):
    m = YEAR.search(s or "")
    return int(m.group(1)) if m else None


# ----------------------------------------------------------------------------------------------
# images: web-sized copies of the history's illustrations
# ----------------------------------------------------------------------------------------------

SIZES = {"t": 420, "m": 1200, "f": 2200}
MEDIA = {}


def make_images():
    srcdir = FAMILY / CFG["image_dir"]
    for f in sorted(srcdir.glob("*.jpg")):
        key = f.stem
        with Image.open(f) as im:
            im = im.convert("RGB")
            w, h = im.size
            MEDIA[key] = {"w": w, "h": h}
            for k, edge in SIZES.items():
                out = DOCS / "media" / k / f"{key}.jpg"
                out.parent.mkdir(parents=True, exist_ok=True)
                s = min(1.0, edge / max(w, h))
                if out.exists() and out.stat().st_mtime > f.stat().st_mtime:
                    continue
                im.resize((round(w * s), round(h * s)), Image.LANCZOS).save(out, quality=84, optimize=True, progressive=True)


def isrc(key, size="m"):
    return "{R}media/" + size + "/" + key + ".jpg"


def img_tag(key, alt, sizes="(max-width: 640px) 100vw, 36rem", lazy=True, cls=""):
    w, h = MEDIA[key]["w"], MEDIA[key]["h"]
    big = max(w, h)
    ss = []
    for k, edge in SIZES.items():
        s = min(1.0, edge / big)
        ss.append(f"{isrc(key, k)} {round(w * s)}w")
        if s == 1.0:
            break
    s = min(1.0, 1200 / big)
    c = f' class="{cls}"' if cls else ""
    lz = ' loading="lazy" decoding="async"' if lazy else ""
    return (f'<img{c} src="{isrc(key)}" srcset="{", ".join(ss)}" sizes="{sizes}" alt="{H(alt)}" '
            f'width="{round(w * s)}" height="{round(h * s)}"{lz}>')


# ----------------------------------------------------------------------------------------------
# sources (03 Sources and citations.md)
# ----------------------------------------------------------------------------------------------

PRIVATE_ROW = re.compile(r"Sylvia M\.? Rodilitz|Victor E\.? Koik", re.I)
SOURCES = OrderedDict()
SRC_SECTIONS = OrderedDict()
SRC_TITLES = {"Original records": "Original records",
              "Indexes and record citations in Barnst's Ancestry tree": "Index entries in the family’s Ancestry tree",
              "Secondary and lead sources": "Secondary and lead sources",
              "Indexes searched (cited for negative results)": "Indexes searched (for negative results)",
              "Other search tools used": "Other search tools used"}
SRC_TXT = (RP / "03 Sources and citations.md").read_text(encoding="utf-8")
cur = None
for line in SRC_TXT.splitlines():
    hm = re.match(r"## (.+)", line)
    if hm:
        cur = hm.group(1).strip()
        continue
    m = re.match(r"\| (RZ-S[\d.]+[a-z]?) \| (.+)\|\s*$", line)
    if not m or not cur or PRIVATE_ROW.search(line):
        continue
    cells = [c.strip() for c in m.group(2).split(" | ")]
    code = m.group(1)
    if cur.startswith("Indexes and record citations"):
        desc = f"{cells[0]}: {cells[1]}" if len(cells) > 1 else cells[0]
        link = cells[2] if len(cells) > 2 else ""
    else:
        desc, link = cells[0], (cells[1] if len(cells) > 1 else "")
    SOURCES[code] = {"code": code, "desc": desc, "link": link, "section": cur}
    SRC_SECTIONS.setdefault(cur, []).append(code)
REC_IMAGES = CFG["record_images"]
SRC_RX = re.compile(r"\bRZ-S(\d{2,3}(?:\.\d+)?[a-z]?)\b")


def src_href(code):
    if code in REC_IMAGES:
        return f"{{R}}records/{code.lower()}.html"
    return f"{{R}}records/index.html#{code}"


def link_sources(s):
    """Turn RZ-S codes in HTML text into links to the records pages (outside existing tags)."""
    def rep(m):
        code = m.group(0)
        if code not in SOURCES:
            base = re.sub(r"\.\d+$", "", code)
            if base not in SOURCES:
                return code
            code = base
        return f'<a class="src" href="{src_href(code)}">{m.group(0)}</a>'
    parts = re.split(r"(<a [^>]*>.*?</a>|<[^>]+>)", s, flags=re.S)
    return "".join(p if p.startswith("<") else SRC_RX.sub(rep, p) for p in parts)


def link_urls(s):
    """Bare URLs in source descriptions become links (the display drops the scheme)."""
    def rep(m):
        u = m.group(0).rstrip(".,;)")
        tail = m.group(0)[len(u):]
        lab = re.sub(r"^https?://(www\.)?", "", u)
        return f'<a href="{H(u)}">{H(shorten(lab, 70))}</a>{tail}'
    parts = re.split(r"(<a [^>]*>.*?</a>|<[^>]+>)", s, flags=re.S)
    return "".join(p if p.startswith("<") else re.sub(r"https?://[^\s<·|]+", rep, p) for p in parts)


# ----------------------------------------------------------------------------------------------
# people (02 Family tree.md + data/people.json)
# ----------------------------------------------------------------------------------------------

PEOPLE = OrderedDict()
TREE_TXT = (RP / "02 Family tree.md").read_text(encoding="utf-8")
ROWS = {}
for line in TREE_TXT.split("## People", 1)[1].split("\n## ", 1)[0].splitlines():
    m = re.match(r"\| ([RHZ]-\d{3}) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|\s*$", line)
    if m:
        ROWS[m.group(1)] = m.groups()


def short_dates(dates):
    if not dates or dates.strip() in ("—", "?"):
        return ""
    parts = re.split(r"\s+–\s+", dates, maxsplit=1)
    b = parts[0]
    d = parts[1] if len(parts) > 1 else ""

    def one(s):
        s2 = re.sub(r"\(.*?\)", "", s or "")
        y = year_of(s2) or year_of(s)
        if not y:
            return ""
        st = s.strip().lower()
        if st.startswith(("c.", "c ", "about", "ca")):
            return f"c. {y}"
        if st.startswith("before"):
            return f"before {y}"
        return str(y)
    by, dy = one(b), one(d)
    if by and dy:
        return f"{by}–{dy}"
    if by:
        return f"b. {by}"
    if dy:
        return f"d. {dy}"
    return ""


for pid, d in PEOPLE_DATA.items():
    row = ROWS.get(pid)
    if not row:
        error(f"{pid} is in people.json but not in 02 Family tree.md")
        continue
    _, tname, dates, born, status, srcs = row
    p = {"id": pid, "name": d["name"], "tree_name": tname, "dates_raw": dates, "born_at": born, "status": status,
         "sources": re.findall(r"RZ-S[\d.]+", srcs), "parents": [x for x in d["parents"]], "spouses": list(d["spouses"]),
         "children": [], "probable": d.get("probable", False), "bio": d.get("bio", ""), "aka": d.get("aka", ""),
         "group": d.get("group", ""), "side": "r" if pid[0] in "RH" else "z"}
    p["dates"] = short_dates(dates)
    by = year_of(dates.split("–")[0]) if dates else None
    p["restricted"] = bool(by and by >= CFG.get("privacy_birth_year", 1930) and not year_of(dates.split("–")[1] if "–" in dates else ""))
    p["url"] = f"people/{pid.lower()}.html"
    PEOPLE[pid] = p
for pid in ROWS:
    if pid not in PEOPLE and pid not in ("Z-067",):
        print(f"NOTE: {pid} is in the family tree file but has no entry in people.json; not shown")
for p in PEOPLE.values():
    for x in p["parents"] + p["spouses"]:
        if x not in PEOPLE:
            error(f"{p['id']}: unknown relative {x}")
for p in PEOPLE.values():
    p["parents"] = [x for x in p["parents"] if x in PEOPLE]
    for par in p["parents"]:
        PEOPLE[par]["children"].append(p["id"])
    for s in p["spouses"]:
        if s in PEOPLE and p["id"] not in PEOPLE[s]["spouses"]:
            PEOPLE[s]["spouses"].append(p["id"])


def date_key(p):
    return (year_of(p["dates_raw"]) or 3000, p["id"])


for p in PEOPLE.values():
    p["children"].sort(key=lambda i: date_key(PEOPLE[i]))


def plink(pid, show_dates=True):
    p = PEOPLE.get(pid)
    if not p:
        return H(pid)
    d = f' <span class="d">{H(p["dates"])}</span>' if (show_dates and p["dates"] and not p["restricted"]) else ""
    return f'<a class="pn {p["side"]}" href="{{R}}{p["url"]}">{H(p["name"])}</a>{d}'


def siblings(p):
    sib = []
    for par in p["parents"]:
        for c in PEOPLE[par]["children"]:
            if c != p["id"] and c not in sib:
                sib.append(c)
    sib.sort(key=lambda i: date_key(PEOPLE[i]))
    return sib


# ----------------------------------------------------------------------------------------------
# research notes (01 Findings.md): sections whose heading names a person ID
# ----------------------------------------------------------------------------------------------

FINDINGS = (RP / "01 Findings.md").read_text(encoding="utf-8")
NOTES_BY_PERSON = defaultdict(list)
SKIP_FINDINGS = re.compile(r"How this branch joins|Writing to the European archives|Setup", re.I)
for part in re.split(r"\n(?=## )", FINDINGS):
    hm = re.match(r"## (.+)", part)
    if not hm or SKIP_FINDINGS.search(hm.group(1)):
        continue
    ids = re.findall(r"\b([RHZ]-\d{3})\b", hm.group(1))
    title = scrub(hm.group(1)).strip()
    title = re.sub(r"\s*\((?:\d{1,2} \w+ 2026|from[^)]*|[^)]*2026[^)]*)\)\s*", " ", title).strip()
    body = "\n".join(l for l in part[hm.end():].splitlines() if not DROP_LINE.search(l)).strip()
    for pid in dict.fromkeys(ids):
        if pid in PEOPLE:
            NOTES_BY_PERSON[pid].append((title, body))


# ----------------------------------------------------------------------------------------------
# the history (master text)
# ----------------------------------------------------------------------------------------------

def svg_asset(name):
    t = (HERE / "assets" / name).read_text(encoding="utf-8")
    t = re.sub(r"<\?xml[^>]*>\s*", "", t)
    return t


TREE_SVG = svg_asset("tree_overview.svg")
MAP1_SVG = (f'<div class="svgfig">{svg_asset("maps/map1_over.svg")}</div>'
            f'<div class="mappair"><div class="svgfig">{svg_asset("maps/map1_a.svg")}</div><div class="svgfig">{svg_asset("maps/map1_b.svg")}</div></div>')
MAP2_SVG = f'<div class="svgfig">{svg_asset("maps/map2.svg")}</div>'

body_md = re.sub(r"<!--.*?-->", "", MASTER, flags=re.S)
for old, new in CFG.get("text_overrides", []):
    if old in body_md:
        body_md = body_md.replace(old, new)
    else:
        error(f"text override no longer matches the master text: {old[:60]}…")
FN = {}


def _grab(m):
    FN[m.group(1)] = m.group(0).rstrip("\n")
    return ""


body_md = re.sub(r"^\[\^([\w-]+)\]:.*?(?=\n\n|\Z)", _grab, body_md, flags=re.M | re.S)
COVER = re.search(r'<section class="cover"[^>]*>(.*?)</section>', body_md, re.S).group(1)
SECTIONS = OrderedDict()
for m in re.finditer(r'<section class="section ([^"]*)" id="([^"]+)" markdown="1">\s*<h2><span class="kicker">([^<]*)</span>(.*?)</h2>(.*?)</section>',
                     body_md, re.S):
    cls, sid, kicker, title, body = m.groups()
    strand = "r" if " r" in f" {cls}" else "z" if " z" in f" {cls} " or cls.startswith("z") else "sh"
    strand = cls.split()[0] if cls.split()[0] in ("r", "z", "sh") else strand
    SECTIONS[sid] = {"id": sid, "kicker": kicker.strip(), "title": strip_tags(title).strip(), "body": body, "strand": strand}

CHAPTER_ORDER = ["overview", "world", "rodilitz", "morris", "saslow", "zaslow", "together",
                 "chronology", "stayed", "places", "details", "questions", "sources"]
MAP_AFTER = {"overview": ("map1", MAP1_SVG), "morris": ("map2", MAP2_SVG)}
CH_SUMMARY = CFG["chapter_summaries"]
CHAPTER_HTML, CH_H3 = {}, {}
FIG_IN_CHAPTER = {}


def figure_html(m, cs):
    attrs, inner = m.group(1), m.group(2)
    im = re.search(r'<img src="img/([\w-]+)\.\w+" alt="([^"]*)">', inner)
    cap = re.search(r"<figcaption>(.*?)</figcaption>", inner, re.S)
    if not im:
        return m.group(0)
    key, alt = im.group(1), im.group(2)
    if key not in MEDIA:
        error(f"{cs}: no image for {key}")
        return ""
    FIG_IN_CHAPTER.setdefault(key, cs)
    capx = cap.group(1).strip() if cap else ""
    cls = re.search(r'class="([^"]*)"', attrs)
    cls = cls.group(1) if cls else "single"
    w, h = MEDIA[key]["w"], MEDIA[key]["h"]
    shape = "wide" if w / h > 1.25 else "portrait" if w / h < 0.85 else "single"
    strand = "r" if re.search(r"\br\b", cls) else "z" if re.search(r"\bz\b", cls) else "sh"
    a = f'<a class="lb" href="{isrc(key, "f")}" data-cap="{H(strip_tags(capx))}">{img_tag(key, alt)}</a>'
    return f'<figure class="{shape} {strand}">{a}<figcaption>{capx}</figcaption></figure>'


def person_links_in(htmlb, cs):
    for phrase, pid in CFG["bold_links"].get(cs, {}).items():
        if pid in PEOPLE:
            tgt = f"<strong>{phrase}</strong>"
            if tgt in htmlb:
                htmlb = htmlb.replace(tgt, f'<strong><a class="pn {PEOPLE[pid]["side"]}" href="{{R}}{PEOPLE[pid]["url"]}">{phrase}</a></strong>', 1)
            else:
                print(f"NOTE: {cs}: bold link phrase not found: {phrase}")
    return htmlb


def render_chapter(cs):
    sec = SECTIONS[cs]
    body = sec["body"]
    body = body.replace("<p>{{TREE}}</p>", TREE_SVG).replace("{{TREE}}", TREE_SVG)
    refs = []
    for r in re.findall(r"\[\^([\w-]+)\](?!:)", body):
        if r not in refs:
            refs.append(r)
    for r in refs:
        if r not in FN:
            error(f"{cs}: footnote [^{r}] has no definition")
    pre = body + "\n\n" + "\n\n".join(scrub(FN[r]) for r in refs if r in FN) + "\n"
    htmlb = markdown.markdown(pre, extensions=["tables", "footnotes", "md_in_html", "sane_lists", "attr_list"],
                              extension_configs={"footnotes": {"BACKLINK_TEXT": "↩", "BACKLINK_TITLE": "Back to note %d in the text",
                                                               "SEPARATOR": "-", "UNIQUE_IDS": False}})
    htmlb = re.sub(r"<figure( class=\"(?:single|wide)[^\"]*\")>(.*?)</figure>", lambda m: figure_html(m, cs), htmlb, flags=re.S)
    htmlb = re.sub(r'<figure class="treefig wide">(.*?)<figcaption>(.*?)</figcaption></figure>',
                   lambda m: (f'<figure class="treefig sh"><div class="svgfig">{m.group(1)}</div><figcaption>{m.group(2)} '
                              f'<a href="{{R}}tree/index.html">Open the interactive family tree</a>.</figcaption></figure>'), htmlb, flags=re.S)
    htmlb = re.sub(r'<div class="tablewrap[^"]*">\s*(<table>.*?</table>)\s*</div>', r'<div class="tblwrap" tabindex="0">\1</div>', htmlb, flags=re.S)
    htmlb = re.sub(r"(?<!tabindex=\"0\">)(<table>.*?</table>)(?!\s*</div>)", r'<div class="tblwrap" tabindex="0">\1</div>', htmlb, flags=re.S)
    htmlb = htmlb.replace('class="evidence"', 'class="note evidence"')
    h3s = []

    def _h3(mm):
        t = strip_tags(mm.group(1))
        hid = slug(t)
        h3s.append((hid, t))
        return f'<h2 id="{hid}">{mm.group(1)}</h2>'
    htmlb = re.sub(r"<h3>(.*?)</h3>", _h3, htmlb)
    if cs in MAP_AFTER:
        mid, svg = MAP_AFTER[cs]
        msec = SECTIONS.get(mid)
        if msec:
            mt = msec["title"]
            sub = re.search(r'<p class="map-sub">(.*?)</p>', msec["body"], re.S)
            leg = re.search(r'<div class="map-legend" markdown="1">(.*?)</div>', msec["body"], re.S)
            h3s.append((mid, f"{msec['kicker']}: {mt}"))
            htmlb_map = (f'<h2 id="{mid}">{H(msec["kicker"])}: {H(mt)}</h2>'
                         + (f'<p class="small">{sub.group(1)}</p>' if sub else "") + svg
                         + (f'<p class="small">{md(leg.group(1).strip(), inline=True)}</p>' if leg else "")
                         + '<p class="small"><a href="{R}map/index.html">Explore these places on the interactive map</a>.</p>')
            fm0 = re.search(r'<div class="footnote">', htmlb)
            htmlb = htmlb[:fm0.start()] + htmlb_map + htmlb[fm0.start():] if fm0 else htmlb + htmlb_map
    fm = re.search(r'<div class="footnote">.*</div>\s*$', htmlb, re.S)
    notes = ""
    if fm:
        notes = (f'<section class="notes" aria-labelledby="notes-h"><h2 id="notes-h">Notes</h2>{link_urls(link_sources(fm.group(0)))}'
                 f'<p class="small"><a href="#top">Back to the top of the chapter</a></p></section>')
        htmlb = htmlb[:fm.start()]
    htmlb = person_links_in(htmlb, cs)
    if cs == "sources":
        htmlb = re.sub(r"codes beginning RZ-T refer to the research reports[^.]*\.", "", htmlb)
    htmlb = link_sources(htmlb)
    for t in re.findall(r"\[\^[\w-]+\]|\{\{\w+\}\}", htmlb + notes):
        error(f"{cs}: unresolved token {t}")
    CHAPTER_HTML[cs] = htmlb + notes
    CH_H3[cs] = h3s


CH_BY_PERSON = defaultdict(list)
for cs_, pids in CHAPTER_PEOPLE.items():
    for pid in pids:
        if pid not in PEOPLE:
            error(f"chapter_people.json: unknown person {pid} in {cs_}")
        CH_BY_PERSON[pid].append(cs_)


def toc_list(cs):
    return "<ol>" + "".join(f'<li><a href="#{a}">{H(t)}</a></li>' for a, t in CH_H3[cs]) + "</ol>"


def build_history():
    order = [c for c in CHAPTER_ORDER if c in CHAPTER_HTML]
    for idx, cs in enumerate(order):
        sec = SECTIONS[cs]
        ttl, kicker, strand = sec["title"], sec["kicker"], sec["strand"]
        rail, mobile_toc = [], ""
        if CH_H3[cs]:
            rail.append(f'<nav class="panel toc-panel" aria-label="In this chapter"><h2>In this chapter</h2>{toc_list(cs)}</nav>')
            mobile_toc = f'<details class="chapter-toc"><summary>In this chapter</summary>{toc_list(cs)}</details>'
        pl = [pid for pid in CHAPTER_PEOPLE.get(cs, []) if pid in PEOPLE]
        if pl:
            rail.append('<section class="rail-people"><h2>People in this chapter</h2><ul class="pl">'
                        + "".join(f"<li>{plink(pid)}</li>" for pid in pl) + "</ul></section>")
        rail.append('<section class="rail-more"><h2>Explore</h2><ul><li><a href="{R}tree/index.html">Family tree</a></li>'
                    '<li><a href="{R}map/index.html">Map of places</a></li><li><a href="{R}research/index.html">Research since the printed edition</a></li>'
                    f'<li><a href="{{R}}downloads/{PDF_NAME}">The history as a PDF</a></li></ul></section>')
        prev = order[idx - 1] if idx > 0 else None
        nxt = order[idx + 1] if idx + 1 < len(order) else None
        nav = '<nav class="chapnav" aria-label="Chapters">'
        nav += (f'<a class="prev" href="{prev}.html"><span class="dir">Previous</span><span class="t">{H(SECTIONS[prev]["title"])}</span></a>' if prev else "<span></span>")
        nav += (f'<a class="next" href="{nxt}.html"><span class="dir">Next</span><span class="t">{H(SECTIONS[nxt]["title"])}</span></a>' if nxt else "<span></span>")
        nav += "</nav>"
        onecol = " onecol" if cs == "overview" else ""
        body = (f'<div class="chapter {strand}{onecol}"><article class="reading" id="top">'
                + head_block(H(kicker), H(ttl), CH_SUMMARY.get(cs, ""), strand) + mobile_toc
                + f'<div class="text">{CHAPTER_HTML[cs]}</div>{nav}</article>'
                + f'<aside class="rail" aria-label="Chapter guide"><div class="sticky">{"".join(rail)}</div></aside></div>')
        first = next((k for k, c in FIG_IN_CHAPTER.items() if c == cs), None)
        WRITTEN.append(page(f"history/{cs}.html", ttl, body, "history", desc=f"{ttl}: {CH_SUMMARY.get(cs, '')}", surface=False,
                            image=isrc(first) if first else None, crumbs=[("The story", "history/index.html"), (ttl, None)]))
    rows, prev, prevgrp = [], None, None
    for cs in order:
        sec = SECTIONS[cs]
        kicker = sec["kicker"]
        grpkey = "Appendix" if kicker.startswith("Appendix") else kicker
        newgrp = " grp" if prev is not None and grpkey != prevgrp and (grpkey == "Appendix" or prevgrp == "Appendix") else ""
        prev, prevgrp = kicker, grpkey
        rows.append(f'<a class="row {sec["strand"]}{newgrp}" href="{cs}.html"><span class="k">{H(kicker)}</span>'
                    f'<span><span class="t">{H(sec["title"])}</span><span class="s">{H(CH_SUMMARY.get(cs, ""))}</span></span></a>')
    intro = re.search(r'<p class="cover-intro">(.*?)</p>', COVER, re.S).group(1)
    body = (head_block("The story", "From Grodno, Volhynia and Podolia to America",
                       "The family history, chapter by chapter, with its records, maps and notes.")
            + f'<div class="prose"><p>{intro}</p><p class="actions"><a class="btn" href="overview.html">Start reading</a>'
              f'<a class="btn ghost" href="{{R}}downloads/{PDF_NAME}">{icon("download", 18)} Download the PDF</a></p>'
              f'<p class="small">The text is the {H(EDITION_PHRASE)}. Research found since then is on the <a href="{{R}}research/index.html#since">Research</a> page.</p></div>'
            + f'<div class="toc">{"".join(rows)}</div>')
    WRITTEN.append(page("history/index.html", "The story", body, "history",
                        desc="The family history of the Rodilitzes, Hausmans, Saslows and Zaslows, chapter by chapter."))


# ----------------------------------------------------------------------------------------------
# people pages
# ----------------------------------------------------------------------------------------------

GROUPS = [
    ("r", "rodilitz", "The Rodilitz family", "Jacob Rodilitz and Mary Prozansky, their children and grandchildren, and Mary’s family."),
    ("r", "hausman", "The Hausman family", "Sylvia Hausman, Theodore’s mother, and her parents and sisters."),
    ("r", "inlaws", "Married into the Rodilitz family", "Husbands and wives of Jacob and Mary’s children."),
    ("z", "zaslow", "The Zaslow family", "Benjamin Zaslow, his parents Jacob and Miriam, his brothers, and his children."),
    ("z", "saslow", "The Saslow family", "Benjamin and Bessie Saslow, their children, and the generation before them."),
    ("z", "unplaced", "Relatives not yet placed", "People in the records who are probably related but whose place in the family is not yet known."),
]


def group_of(p):
    if p["group"] == "unplaced":
        return "unplaced"
    pid = p["id"]
    if pid[0] == "H":
        return "hausman"
    if pid in ("R-051", "R-052", "R-053", "R-054", "R-055", "R-056"):
        return "inlaws"
    if pid[0] == "R":
        return "rodilitz"
    if pid in ("Z-011", "Z-012", "Z-013", "Z-014", "Z-015", "Z-020", "Z-021", "Z-030", "Z-031", "Z-040", "Z-066", "Z-068"):
        return "saslow"
    return "zaslow"


def fam_row(label, ids, extra=""):
    if not ids and not extra:
        return ""
    links = ", ".join(plink(i) for i in ids)
    if extra:
        links = (links + " " if links else "") + f'<span class="q">{extra}</span>'
    return f'<div><dt>{label}</dt><dd>{links}</dd></div>'


def relation_line(p):
    bits = []
    if p["parents"]:
        bits.append("Child of " + " and ".join(plink(i, show_dates=False) for i in p["parents"]))
    if p["spouses"]:
        bits.append("married " + " and ".join(plink(i, show_dates=False) for i in p["spouses"]))
    return ("; ".join(bits) + ".") if bits else ""


def source_li(code):
    s = SOURCES.get(code) or SOURCES.get(re.sub(r"\.\d+$", "", code))
    if not s:
        return f"<li>{H(code)}</li>"
    return (f'<li><a class="code" href="{src_href(s["code"])}">{H(code)}</a> '
            f'{md(shorten(strip_tags(md(scrub(s["desc"]), inline=True)), 170), inline=True)}</li>')


def build_people():
    for p in PEOPLE.values():
        st = p["side"]
        fam = group_of(p)
        kick = {"rodilitz": "Rodilitz family", "hausman": "Hausman family", "inlaws": "Married into the Rodilitz family",
                "zaslow": "Zaslow family", "saslow": "Saslow family", "unplaced": "Not yet placed"}[fam]
        kick += " · Theodore’s side" if st == "r" else " · Doris’s side"
        crumbs = [("People", "people/index.html"), (p["name"], None)]
        local = [("about", "About"), ("family", "Family")]
        parts = []
        intro = f"<p>{H(p['bio'])}</p>" if p["bio"] else (f"<p>{relation_line(p)}</p>" if relation_line(p) else "")
        chs = [c for c in CH_BY_PERSON.get(p["id"], []) if c in SECTIONS]
        if chs:
            intro += ('<p class="small">In the family history: ' + " · ".join(
                f'<a href="{{R}}history/{c}.html">{H(SECTIONS[c]["title"])}</a>' for c in chs) + "</p>")
        parts.append(f'<section id="about" class="bio">{intro or "<p>This person appears in the research but not yet in the family history.</p>"}</section>')
        famd = (fam_row("Parents", p["parents"], "(probable, not proven)" if p["probable"] and p["parents"] else "")
                + fam_row("Husband or wife" if len(p["spouses"]) == 1 else "Spouses", p["spouses"])
                + fam_row("Children", p["children"]) + fam_row("Brothers and sisters", siblings(p)))
        parts.append(f'<section id="family"><h2 class="sec">Family</h2><dl class="fam-links">{famd or "<div><dd>No relationships recorded yet.</dd></div>"}</dl>'
                     f'<p class="small"><a href="{{R}}tree/index.html#{p["id"]}">See {H(p["name"])} in the family tree</a></p></section>')
        imgs = [c for c in p["sources"] if c in REC_IMAGES]
        if imgs:
            local.append(("records", "Records"))
            th = []
            for c in imgs:
                key, cap = REC_IMAGES[c]
                th.append(f'<figure><a class="lb" href="{isrc(key, "f")}" data-cap="{H(c + " · " + cap)}" data-page="{{R}}records/{c.lower()}.html">'
                          f'<span class="ti"><img src="{isrc(key, "t")}" alt="{H(cap)}" loading="lazy"></span></a>'
                          f'<figcaption><a href="{{R}}records/{c.lower()}.html"><span class="code">{c}</span> {H(cap)}</a></figcaption></figure>')
            parts.append(f'<section id="records"><h2 class="sec">Records</h2><div class="thumbs">{"".join(th)}</div></section>')
        rn = []
        rows = []
        if p["aka"]:
            rows.append(f'<tr><th scope="row">Also recorded as</th><td>{H(p["aka"])}</td></tr>')
        rows.append(f'<tr><th scope="row">Name in the research files</th><td>{md(scrub(p["tree_name"]), inline=True)}</td></tr>')
        if p["dates_raw"].strip() not in ("?", "—", "? – ?"):
            rows.append(f'<tr><th scope="row">Dates</th><td>{link_sources(md(scrub(p["dates_raw"]), inline=True))}</td></tr>')
        if p["born_at"].strip() not in ("?", "—"):
            rows.append(f'<tr><th scope="row">Born or from</th><td>{md(scrub(p["born_at"]), inline=True)}</td></tr>')
        if p["status"].strip() not in ("—", "-"):
            rows.append(f'<tr><th scope="row">Place in the family</th><td>{link_sources(md(scrub(p["status"]), inline=True))}</td></tr>')
        rn.append('<h3>As recorded in the research files</h3><table class="facts">' + "".join(rows) + "</table>")
        if p["sources"]:
            rn.append('<h3>Key sources</h3><ul class="srclist">' + "".join(source_li(c) for c in p["sources"]) + "</ul>")
        for title, body in NOTES_BY_PERSON.get(p["id"], []):
            nh = link_urls(link_sources(md(scrub(body))))
            rn.append(f'<h3>{H(title)}</h3><div class="prose">{nh}</div>')
        if rn:
            local.append(("research", "Research notes"))
            parts.append('<section id="research"><details class="research"><summary><span class="sumt">Working research notes</span>'
                         '<span class="sums">What each record says, with the readings that are still uncertain. '
                         'The family history gives the edited account.</span></summary>' + "".join(rn) + "</details></section>")
        lnav = '<nav class="localnav" aria-label="On this page">' + "".join(f'<a href="#{a}">{t}</a>' for a, t in local) + "</nav>"
        body = (f'<header class="page-head {st}"><div class="person-head"><div><span class="kicker">{H(kick)}</span>'
                f'<h1>{H(p["name"])}</h1><p class="dek">{H(p["dates"])}</p>{lnav}</div></div></header>'
                f'<div class="person {st}">{"".join(parts)}</div>')
        desc = p["bio"] or f"{p['name']} {p['dates']}: family, records and research notes in the Rodilitz and Zaslow family history."
        WRITTEN.append(page(p["url"], p["name"], body, "people", desc=desc, crumbs=crumbs))
    groups = []
    for side, key, title, note in GROUPS:
        ps = [p for p in PEOPLE.values() if group_of(p) == key]
        if not ps:
            continue
        ps.sort(key=date_key)
        items = "".join(
            f'<li data-q="{H(p["name"] + " " + p["aka"] + " " + p["tree_name"] + " " + p["id"])}"><a href="{{R}}{p["url"]}"><span class="n">{H(p["name"])}</span>'
            f'<span class="d">{H(p["dates"])}</span>{BIO_MARK if p["bio"] else ""}</a></li>' for p in ps)
        groups.append(f'<section class="pgroup {side}" data-group="1"><h2>{H(title)}</h2><p class="gnote">{H(note)}</p><ul class="plist">{items}</ul></section>')
    principal = ["R-001", "Z-001", "R-010", "H-010", "Z-010", "Z-011", "R-020", "R-021", "Z-020", "Z-021"]
    start = "".join(f'<li>{plink(i)}</li>' for i in principal if i in PEOPLE)
    body = (head_block("People", "Everyone in the research",
                       f"{len(PEOPLE)} people from passenger lists, censuses, naturalization papers, certificates, gravestones and the registers of their home towns.")
            + f'<div class="panel start"><h2>Start with</h2><ul class="startlist">{start}</ul></div>'
            + filterbar("pq", "Find a person", "Name, spelling or ID", "#plists", "people")
            + f'<div id="plists">{"".join(groups)}</div>')
    WRITTEN.append(page("people/index.html", "People", body, "people",
                        desc=f"The {len(PEOPLE)} people in the Rodilitz and Zaslow research, with biographies, records and research notes."))


BIO_MARK = '<span class="bio-mark">biography</span>'


def filterbar(fid, label, ph, target, noun):
    return (f'<div class="filterbar" role="search"><label for="{fid}">{label}</label>'
            f'<input id="{fid}" type="search" placeholder="{ph}" data-filter="{target}" data-noun="{noun}" autocomplete="off">'
            f'<button type="button" class="reset" data-reset="{fid}" hidden>Clear</button>'
            f'<span class="count" role="status" aria-live="polite" data-count="{fid}"></span></div>'
            f'<p class="noresults" data-none="{fid}" hidden>No matching {noun}. Try another spelling, or <button type="button" class="linkbtn" data-reset="{fid}">clear the search</button>.</p>')


# ----------------------------------------------------------------------------------------------
# records
# ----------------------------------------------------------------------------------------------

def people_for_source(code):
    return [p["id"] for p in PEOPLE.values() if code in p["sources"]]


def src_desc_html(s):
    d = scrub(s["desc"])
    d = re.sub(r"^\*\*[^*]*\((?:high|medium|low|lead)[^*]*\)\.?\*\*\s*", "", d, flags=re.I)
    return link_urls(link_sources(md(d, inline=True)))


def build_records():
    secs = []
    for sec, codes in SRC_SECTIONS.items():
        rows = []
        for c in codes:
            s = SOURCES[c]
            link = scrub(s["link"])
            link_h = link_urls(md(link, inline=True)) if link.strip() not in ("—", "-", "") else ""
            ppl = people_for_source(c)
            who = (' <span class="acc">· ' + ", ".join(plink(i, show_dates=False) for i in ppl) + "</span>") if ppl else ""
            imgm = f' <a class="acc" href="{{R}}records/{c.lower()}.html">· image</a>' if c in REC_IMAGES else ""
            rows.append(f'<div class="srcrow" id="{c}" data-q="{H(scrub(strip_tags(s["desc"])) + " " + c)}"><span class="code">{c}</span>'
                        f'<div><div class="d">{src_desc_html(s)}{imgm}</div>'
                        + (f'<div class="acc">{link_h}</div>' if link_h else "") + f'{who}</div></div>')
        secs.append(f'<section class="pgroup sh" data-group="1"><h2>{H(SRC_TITLES.get(sec, sec))}</h2>{"".join(rows)}</section>')
    th = []
    for c, (key, cap) in REC_IMAGES.items():
        th.append(f'<figure><a href="{c.lower()}.html"><span class="ti"><img src="{isrc(key, "t")}" alt="{H(cap)}" loading="lazy"></span></a>'
                  f'<figcaption><a href="{c.lower()}.html"><span class="code">{c}</span> {H(cap)}</a></figcaption></figure>')
        s = SOURCES.get(c, {"desc": cap, "link": ""})
        ppl = people_for_source(c)
        link = scrub(s.get("link", ""))
        cite = f"{strip_tags(md(scrub(s['desc']), inline=True))} {SITE_TITLE}, compiled by {CFG['editor']}."
        body = (head_block(f"Record · {c}", H(cap), "", "sh")
                + f'<figure class="single sh recimg"><a class="lb" href="{isrc(key, "f")}" data-cap="{H(cap)}">{img_tag(key, cap, lazy=False)}</a></figure>'
                + '<div class="prose"><h2 class="sec">What it is</h2>'
                + f'<p>{src_desc_html(s)}</p>'
                + (f'<p class="small">Original: {link_urls(md(link, inline=True))}</p>' if link.strip() not in ("", "—") else "")
                + (('<h2 class="sec">People in this record</h2><p>' + " · ".join(plink(i) for i in ppl) + "</p>") if ppl else "")
                + (f'<p class="small">In the family history: <a href="{{R}}history/{FIG_IN_CHAPTER[key]}.html">{H(SECTIONS[FIG_IN_CHAPTER[key]]["title"])}</a></p>' if key in FIG_IN_CHAPTER else "")
                + f'<h2 class="sec">How to cite</h2><p class="small">{H(cite)}</p></div>')
        WRITTEN.append(page(f"records/{c.lower()}.html", f"{c} · {shorten(cap, 60)}", body, "records",
                            crumbs=[("Records", "records/index.html"), (c, None)], image=isrc(key)))
    body = (head_block("Records", "The records behind the history",
                       f"Every source used in the research has a permanent code and, where one exists, a permanent link. {len(SOURCES)} sources are listed.")
            + '<div class="prose"><p>Most of the records are online in the collections named. The images below are those reproduced in the family history; '
              'the rest can be opened from their links (some need a free FamilySearch or a paid Ancestry account). '
              'Sources marked as searched with no result are listed too, so the same ground need not be covered twice.</p></div>'
            + f'<h2 class="sec">Records shown in the history</h2><div class="thumbs">{"".join(th)}</div>'
            + filterbar("rq", "Find a source", "Name, place, ship or code", "#slists", "sources")
            + f'<div id="slists">{"".join(secs)}</div>')
    WRITTEN.append(page("records/index.html", "Records", body, "records",
                        desc="The records behind the Rodilitz and Zaslow family history: passenger lists, certificates, censuses, naturalizations and registers."))


# ----------------------------------------------------------------------------------------------
# tree, map, research, about, home
# ----------------------------------------------------------------------------------------------

def build_tree():
    data = {}
    for p in PEOPLE.values():
        data[p["id"]] = {"n": p["name"], "s": p["name"], "d": "" if p["restricted"] else p["dates"], "f": p["side"],
                         "p": p["parents"], "sp": p["spouses"], "c": p["children"], "u": p["url"], "q": 1 if p["probable"] else 0,
                         "r": 1 if p["restricted"] else 0}
    (DOCS / "assets").mkdir(parents=True, exist_ok=True)
    (DOCS / "assets" / "people.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    seen = set()

    def node(pid, depth=0):
        p = PEOPLE[pid]
        if pid in seen:
            return f'<li><span class="leaf"></span>{plink(pid)} <span class="dt">(shown above)</span></li>'
        seen.add(pid)
        sp = ", ".join(plink(s) for s in p["spouses"])
        sp = f' <span class="sp">= {sp}</span>' if sp else ""
        q = ' <span class="dt">(probable)</span>' if p["probable"] and p["parents"] else ""
        who = f'<span class="who">{plink(pid)}</span>{q}{sp}'
        kids = sorted(set(p["children"]) | {c for s in p["spouses"] for c in PEOPLE[s]["children"] if pid in PEOPLE[c]["parents"]},
                      key=lambda i: date_key(PEOPLE[i]))
        if not kids:
            return f'<li><span class="leaf"></span>{who}</li>'
        op = " open" if depth < 6 else ""
        return f"<li><details{op}><summary>{who}</summary><ul>{''.join(node(k, depth + 1) for k in kids)}</ul></details></li>"
    outlines = []
    for r in CFG["tree_roots"]:
        if r in PEOPLE and r not in seen:
            p = PEOPLE[r]
            outlines.append(f'<section class="pgroup {p["side"]}"><h3>Descendants of {H(p["name"])}</h3><div class="outline"><ul>{node(r)}</ul></div></section>')
    body = (head_block("Family tree", "The family tree",
                       "Choose a person to see their parents, husband or wife, and children. Select any name to move through the tree.")
            + '<div class="tree-tools"><label for="tsel">Person</label><select id="tsel"></select>'
              '<span class="gen" role="group" aria-label="Generations shown"><span class="lbl">Show</span>'
              '<button type="button" data-up="1" aria-pressed="true">Parents</button><button type="button" data-up="2" aria-pressed="false">Grandparents</button>'
              '<button type="button" data-up="3" aria-pressed="false">Great-grandparents</button></span>'
              '<button type="button" class="btn ghost small" id="tcenter">Center</button></div>'
            + '<div class="tree-legend"><span><span class="sw" style="border-color:var(--r-key)"></span>Theodore’s side: Rodilitz, Hausman</span>'
              '<span><span class="sw" style="border-color:var(--z-key)"></span>Doris’s side: Zaslow, Saslow</span>'
              '<span><span class="sw dash"></span>probable, not proven</span><span>▸ more generations beyond</span></div>'
            + '<p class="small hint">On a small screen, drag sideways to see the whole chart.</p>'
            + '<div class="tree-scroll" id="tscroll" tabindex="0" aria-label="Family tree chart"><div class="tree-canvas" id="tcanvas"></div></div>'
            + '<div class="tree-side" id="tside" aria-live="polite"></div>'
            + '<h2 class="sec">Overview</h2><p class="small">Theodore and Doris, their parents and grandparents, as printed in the family history.</p>'
            + f'<div class="svgfig treefig">{TREE_SVG}</div>'
            + '<h2 class="sec">All family lines as a list</h2><p class="small">Descendants of the earliest known ancestor in each line. '
              'This list is the text version of the tree. Use + and – to open or close a branch.</p>'
            + "".join(outlines))
    WRITTEN.append(page("tree/index.html", "Family tree", body, "tree", scripts='<script src="{R}assets/tree.js"></script>',
                        desc="An interactive family tree of the Rodilitz, Hausman, Saslow and Zaslow families, with a text version of every line."))


def build_map():
    pl = []
    for pc in PLACES["places"]:
        q = dict(pc)
        for i in pc.get("people", []):
            if i not in PEOPLE:
                error(f"places.json: unknown person {i} at {pc['id']}")
        q["people"] = [{"id": i, "n": PEOPLE[i]["name"], "u": PEOPLE[i]["url"], "f": PEOPLE[i]["side"]} for i in pc.get("people", []) if i in PEOPLE]
        if q.get("chapter") and q["chapter"] not in SECTIONS:
            error(f"places.json: unknown chapter {q['chapter']}")
        pl.append(q)
    (DOCS / "assets" / "places.json").write_text(json.dumps({"places": pl, "routes": PLACES["routes"], "views": PLACES["views"]}, ensure_ascii=False), encoding="utf-8")
    plist = "".join(f'<li><a href="?place={p["id"]}" data-p="{p["id"]}" class="pn {p["fam"] if p["fam"] in ("r", "z") else "sh"}">{H(p["name"])}</a></li>'
                    for p in PLACES["places"])
    body = (head_block("Map", "Places in the family story",
                       "From Kovel, Kobrin and the Podolian market towns to the ports, Ellis Island, Brooklyn and Philadelphia. Select a place to see what happened there.")
            + '<div class="viewbtns" role="group" aria-label="Map view">'
              '<button type="button" data-view="homes">The home towns</button><button type="button" data-view="crossings">The crossings, 1892–1925</button>'
              '<button type="button" data-view="america">Brooklyn and Philadelphia</button><button type="button" data-view="usa">Across America</button>'
              '<button type="button" data-view="all">Everything</button></div>'
            + '<div class="mapshell"><div class="mapwrap"><div id="map" role="region" aria-label="Interactive map"></div>'
              '<div class="mapfail" id="mapfail" hidden><p><b>The background map could not load.</b> The places and routes still work, '
              'the list of places is beside the map, and the printed maps are below.</p></div></div>'
              f'<div class="mappanel" id="mappanel" aria-live="polite"><h2>Places</h2><p class="small">Select a marker or a name to see what happened there.</p><ul class="placelist">{plist}</ul></div></div>'
            + '<div class="maplegend"><span><span class="c"></span>Theodore’s side: Rodilitz, Hausman</span><span><span class="s"></span>Doris’s side: Zaslow, Saslow</span>'
              '<span><span class="d"></span>Both sides</span><span><span class="ln"></span>documented crossing</span><span><span class="ln dsh"></span>approximate overland route</span></div>'
              '<p class="small">Lines join recorded places; they do not show the exact roads, railways or sea lanes used. Base map © OpenStreetMap contributors.</p>'
            + f'<h2 class="sec">The maps from the history</h2><h3>Map 1 · The home provinces</h3>{MAP1_SVG}<h3>Map 2 · The crossings, 1892–1925</h3>{MAP2_SVG}')
    WRITTEN.append(page("map/index.html", "Map", body, "map",
                        head='<link rel="stylesheet" href="{R}assets/leaflet/leaflet.css">',
                        scripts='<script src="{R}assets/leaflet/leaflet.js"></script><script src="{R}assets/map.js"></script>',
                        desc="An interactive map of the Rodilitz and Zaslow families’ places: Kovel, Kobrin, Divin, Tulchin, Obodovka, the ports, Brooklyn and Philadelphia."))


STATUS_WORDS = ("Answered", "Partly answered", "Open")


def build_research():
    since = []
    for title, text, pids, codes in CFG["since_edition"]:
        for i in pids:
            if i not in PEOPLE:
                error(f"since_edition: unknown person {i}")
        ppl = " · ".join(plink(i, show_dates=False) for i in pids)
        srcs = ", ".join(f'<a class="src" href="{src_href(c)}">{c}</a>' for c in codes)
        since.append(f'<div class="since"><h3>{H(title)}</h3>{md(text)}<p class="small">People: {ppl}' + (f' · Sources: {srcs}' if srcs else "") + "</p></div>")
    items = []
    for q, title, status, text, pids, codes in CFG["questions"]:
        ppl = " · ".join(plink(i, show_dates=False) for i in pids if i in PEOPLE)
        srcs = ", ".join(f'<a class="src" href="{src_href(c)}">{c}</a>' for c in codes if c in SOURCES)
        for c in codes:
            if c not in SOURCES:
                error(f"questions: unknown source {c}")
        extra = (f'<p class="small">People: {ppl}</p>' if ppl else "") + (f'<p class="small">Key sources: {srcs}</p>' if srcs else "")
        items.append(f'<li id="{q}"><details><summary><span class="qid">{q}</span><span class="qt">{H(title)}</span>'
                     f'<span class="st st-{slug(status)}">{status}</span></summary>'
                     f'<div class="qbody"><p class="small">Status: {status}</p>{md(text)}{extra}</div></details></li>')
    counts = {s: sum(1 for x in CFG["questions"] if x[2] == s) for s in STATUS_WORDS}
    stats = " · ".join(f"{counts[s]} {s.lower()}" for s in STATUS_WORDS if counts[s])
    body = (head_block("Research", "Research in progress", "What has been established, what is new since the printed edition, and what is still open.")
            + f'<div class="prose">{md(CFG["research_intro"])}</div>'
            + f'<h2 class="sec" id="since">Since the printed edition</h2><div class="prose"><p class="small">Found after the {H(EDITION_PHRASE)} was printed; '
              'these will be added to the next edition of the history.</p></div>' + "".join(since)
            + f'<h2 class="sec" id="questions">The research questions</h2><p class="small">{len(CFG["questions"])} questions: {stats}. '
              'Select a question to see what has been found.</p>'
            + f'<section class="pgroup sh"><ul class="qlist big">{"".join(items)}</ul></section>'
            + '<div class="prose"><p><a href="{R}history/questions.html">Appendix E · Open questions and further research</a> sets out the records still to get, '
              'and <a href="{R}records/index.html">Records</a> lists every source searched.</p></div>')
    WRITTEN.append(page("research/index.html", "Research", body, "research",
                        desc="The research behind the Rodilitz and Zaslow family history: new findings and the questions still open."))


def build_about():
    txt = CFG["about_md"].replace("{PDF}", PDF_NAME).replace("{EDITION}", EDITION).replace("{EDITOR}", CFG["editor"]) \
        .replace("{CORRECTIONS}", CFG["corrections_url"]).replace("{UPDATED}", CFG["site_updated"])
    changes = "".join(f"<li><b>{H(d)}</b> · {H(t)}</li>" for d, t in CFG["site_changes"])
    body = (head_block("About", "About this site", "Who made it, the conventions it follows, and where the material comes from.")
            + f'<div class="prose">{md(txt)}<h2 id="changes">Site changes</h2><ul class="changes">{changes}</ul></div>')
    WRITTEN.append(page("about/index.html", "About", body, "about",
                        desc="About the Rodilitz and Zaslow family-history site: editor, conventions for names and dates, credits and corrections."))


def build_home():
    kick = re.search(r'<div class="cover-kicker">(.*?)</div>', COVER).group(1)
    sub = re.search(r'<div class="cover-sub">(.*?)</div>', COVER).group(1)
    intro = re.search(r'<p class="cover-intro">(.*?)</p>', COVER, re.S).group(1)
    figs = re.findall(r'<figure><img src="img/([\w-]+)\.\w+" alt="([^"]*)"><figcaption>(.*?)</figcaption></figure>', COVER, re.S)
    fig_html = ""
    if figs:
        key, alt, cap = figs[0]
        fig_html = (f'<figure class="hero-fig r"><a class="lb" href="{isrc(key, "f")}" data-cap="{H(strip_tags(cap))}">'
                    f'{img_tag(key, alt, "(max-width: 880px) 100vw, 34rem", lazy=False)}</a><figcaption>{cap}</figcaption></figure>')
    routes = (f'<div class="routes">'
              f'<a class="route primary" href="{{R}}history/index.html">{icon("book")}<span><b>Read the story</b><span>The family history, from the Pale of Settlement to Brooklyn and Philadelphia</span></span></a>'
              f'<a class="route" href="{{R}}people/index.html">{icon("person")}<span><b>Find a person</b><span>Search all {len(PEOPLE)} people in the research</span></span></a>'
              f'<a class="route" href="#evidence">{icon("record")}<span><b>Explore the evidence</b><span>Records, maps, the tree and the research</span></span></a></div>')
    newto = ('<section class="panel newto" aria-labelledby="newto-h"><h2 id="newto-h">New to the family?</h2>'
             f'<p>{CFG["new_to_family"]}</p><p class="note-elmars">{CFG["zaslow_saslow_note"]}</p>'
             '<p><a href="{R}history/overview.html">How the four families connect</a></p></section>')
    sides = []
    for st, title, kick2, text, people in (
            ("r", "Theodore’s side", "Rodilitz and Hausman", CFG["home_r"], ["R-001", "R-010", "H-010", "R-020", "R-021", "H-021"]),
            ("z", "Doris’s side", "Zaslow and Saslow", CFG["home_z"], ["Z-001", "Z-010", "Z-011", "Z-020", "Z-021", "Z-005", "Z-006"])):
        fams = "".join(f'<div><h3>{H(t)}</h3><p>{H(d)} <a href="{{R}}history/{c}.html">Read more</a></p></div>' for t, d, c in CFG["home_fams"][st])
        chips = " · ".join(plink(i, show_dates=False) for i in people)
        sides.append(f'<section class="{st}"><span class="kicker">{H(kick2)}</span><h2>{H(title)}</h2><p>{H(text)}</p>'
                     f'<div class="fams">{fams}</div><p class="people-chips">{chips}</p></section>')
    evidence = [("records/index.html", "record", "Records", "Passenger lists, certificates, censuses, naturalizations and the registers of the home towns."),
                ("map/index.html", "map", "Map", "The home towns, the ports and the streets of Brooklyn and Philadelphia."),
                ("tree/index.html", "tree", "Family tree", "Move through the generations of all four families."),
                ("research/index.html", "question", "Research", "New findings since the printed edition, and the questions still open."),
                ("people/index.html", "person", "People", f"A page for each of the {len(PEOPLE)} people in the research."),
                (f"downloads/{PDF_NAME}", "download", "The PDF edition", f"The family history as a printable book ({EDITION_PHRASE}).")]
    ev = "".join(f'<a class="item" href="{{R}}{u}">{icon(ic)}<span><span class="t">{H(t)}</span><span class="s">{H(s)}</span></span></a>' for u, ic, t, s in evidence)
    body = (f'<section class="hero">{roundel()}<div class="hero-text"><p class="eyebrow">{H(kick)}</p>'
            f'<h1>The <span class="rw">Rodilitz</span> and <span class="zw">Zaslow</span> Families</h1>'
            f'<p class="sub">{H(sub)}</p><p class="intro">{intro}</p>'
            f'<div class="keys"><span class="l">Theodore’s side</span><span class="k">Doris’s side</span></div></div>{fig_html}</section>'
            + routes + newto + f'<div class="sides">{"".join(sides)}</div>'
            + f'<section class="explore" id="evidence" aria-labelledby="ev-h"><h2 id="ev-h">Explore the evidence</h2><div class="grid">{ev}</div></section>')
    WRITTEN.append(page("index.html", SITE_TITLE, body, "", surface=False, image=isrc(figs[0][0]) if figs else None,
                        desc="The families of Theodore Rodilitz and Doris Zaslow, from Grodno, Volhynia and Podolia to Brooklyn and Philadelphia."))
    base = "/" if CFG.get("cname") else CFG.get("base_path", "/")
    nf = head_block("Not found", "This page isn’t here", "It may have moved when the site was rebuilt.") + \
        '<p><a class="btn" href="{R}index.html">Go to the home page</a> <a class="btn ghost" href="{R}people/index.html">Find a person</a></p>'
    page("404.html", "Not found", nf, "", root=base)


# ----------------------------------------------------------------------------------------------
# assets, PDF, checks
# ----------------------------------------------------------------------------------------------

def publish_pdf(src_pdf, dst):
    """Copy the PDF for download, blanking details of living people listed in config "pdf_redact"."""
    phrases = CFG.get("pdf_redact", [])
    try:
        import pymupdf
    except ImportError:
        error("pymupdf is needed to make the redacted PDF (pip install pymupdf)")
        return
    doc = pymupdf.open(src_pdf)
    found = {q: 0 for q in phrases}
    for pg in doc:
        for q in phrases:
            for r in pg.search_for(q):
                pg.add_redact_annot(r, fill=(1, 1, 1))
                found[q] += 1
        pg.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
    for q, n in found.items():
        if not n:
            error(f"PDF redaction phrase not found: {q}")
    doc.save(dst, garbage=3, deflate=True)


def copy_assets():
    dst = DOCS / "assets"
    for f in (HERE / "assets").rglob("*"):
        if f.is_file() and "maps" not in f.parts and f.name != "tree_overview.svg":
            out = dst / f.relative_to(HERE / "assets")
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)
    pdf = FAMILY / CFG["pdf_source"]
    (DOCS / "downloads").mkdir(parents=True, exist_ok=True)
    if pdf.exists():
        publish_pdf(pdf, DOCS / "downloads" / PDF_NAME)
    else:
        error(f"PDF not found: {pdf}")
    (DOCS / ".nojekyll").write_text("")
    (DOCS / "robots.txt").write_text("User-agent: *\nAllow: /\n" if CFG.get("allow_crawlers") else "User-agent: *\nDisallow: /\n")
    if CFG.get("cname"):
        (DOCS / "CNAME").write_text(CFG["cname"].strip() + "\n")
    elif (DOCS / "CNAME").exists():
        (DOCS / "CNAME").unlink()


def prune_stale():
    keep = set(WRITTEN) | {"404.html"}
    for sub in ("people", "records", "history"):
        for f in (DOCS / sub).glob("*.html"):
            rel = f"{sub}/{f.name}"
            if rel not in keep:
                f.unlink()
                print("removed stale page", rel)


def check_site():
    for path in WRITTEN + ["404.html"]:
        f = DOCS / path
        t = f.read_text(encoding="utf-8")
        ids = set(re.findall(r'\sid="([^"]+)"', t))
        for href in re.findall(r'href="([^"]+)"', t):
            if href.startswith(("http", "mailto:", "?", "data:")) or path == "404.html":
                continue
            target, _, frag = href.partition("#")
            if not target:
                if frag and frag not in ids:
                    error(f"{path}: missing fragment #{frag}")
                continue
            tf = (f.parent / target).resolve()
            if not tf.exists():
                error(f"{path}: broken link {href}")
            elif frag and tf.suffix == ".html":
                tt = tf.read_text(encoding="utf-8")
                if f'id="{frag}"' not in tt and frag not in PEOPLE:
                    error(f"{path}: missing fragment {href}")
        for bad in ("RZ-T", "Barnst", "Claude", "coordinator", "Finkelstein", "dorisarchive", "16 Feb 1956"):
            if bad in t:
                error(f"{path}: internal or private text left in page: {bad}")


def main():
    DOCS.mkdir(exist_ok=True)
    make_images()
    for cs in CHAPTER_ORDER:
        if cs in SECTIONS:
            render_chapter(cs)
        else:
            error(f"chapter {cs} not found in master text")
    copy_assets()
    build_history()
    build_people()
    build_records()
    build_tree()
    build_map()
    build_research()
    build_about()
    build_home()
    prune_stale()
    check_site()
    print(f"{len(WRITTEN)} pages written; {len(PEOPLE)} people; {len(SOURCES)} sources")
    if ERRORS:
        print(f"{len(ERRORS)} errors")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
