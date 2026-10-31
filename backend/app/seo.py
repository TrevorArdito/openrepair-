"""Google-friendly pages.

The app is a single-page app, which search engines read poorly. In production the server
fills in each public page's <title>, description, link previews and a plain-HTML copy of
the main content before sending it. The React app then takes over as usual.
Also serves /sitemap.xml and /robots.txt.
"""

import json
from dataclasses import dataclass, field
from html import escape

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.modules.community.models import Entry, EntryRevision, EntryStatus, Kind
from app.modules.dtc.models import Dtc
from app.modules.dtc.structure import CODE_RE, normalize_code
from app.modules.vehicles.models import Vehicle
from app.modules.vehicles.service import PROFILE_COUNTERS, vehicle_out

SITE = "ChrystalClear"
DEFAULT_DESCRIPTION = (
    "Free auto repair information: VIN decoder, recalls, TSBs, trouble codes, repair guides, "
    "torque specs and labor times — written and checked by technicians."
)
NM_TO_LBFT = 0.737562149
L_TO_QT = 1.056688209


@dataclass
class Page:
    title: str
    description: str = DEFAULT_DESCRIPTION
    body: str = ""  # trusted HTML built here with escape()
    jsonld: dict | None = None
    noindex: bool = False
    extra_links: list[str] = field(default_factory=list)


def _clip(text: str | None, n: int = 155) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _list(items, tag="ul") -> str:
    if not items:
        return ""
    return f"<{tag}>" + "".join(f"<li>{escape(str(i))}</li>" for i in items) + f"</{tag}>"


def _article(headline: str, description: str, url: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": headline[:110],
        "description": description,
        "url": url,
        "publisher": {"@type": "Organization", "name": SITE},
        "license": "https://creativecommons.org/licenses/by-sa/4.0/",
    }


def page_for_code(db: Session, raw: str, url: str) -> Page | None:
    code = normalize_code(raw)
    if not CODE_RE.match(code):
        return None
    d = db.scalar(select(Dtc).where(Dtc.code == code, Dtc.make_id.is_(None)))
    if d is None:
        return Page(title=f"{code} trouble code | {SITE}", description=f"What the OBD-II code {code} means and how to diagnose it.",
                    body=f"<h1>{escape(code)}</h1>")  # fmt: skip
    desc = _clip(f"{d.code}: {d.title}. {d.description}")
    body = (
        f"<h1>{escape(d.code)} — {escape(d.title)}</h1><p>{escape(d.description)}</p>"
        f"<h2>Symptoms</h2>{_list(d.symptoms)}<h2>Common causes</h2>{_list(d.causes)}"
        f"<h2>How to diagnose</h2>{_list(d.diagnostic_steps, 'ol')}"
    )
    return Page(title=f"{d.code}: {d.title} | {SITE}", description=desc, body=body,
                jsonld=_article(f"{d.code}: {d.title}", desc, url))  # fmt: skip


def _spec_line(kind: Kind, data: dict) -> str:
    if kind == Kind.torque_spec and data.get("stages"):
        nm = data["stages"][0].get("value_nm") or 0
        return f"{data.get('component', '')}: {nm * NM_TO_LBFT:.0f} lb·ft ({nm:.0f} N·m)"
    if kind == Kind.fluid_capacity and data.get("amount"):
        amt, unit = data["amount"], data.get("amount_unit", "L")
        extra = f" ({amt * L_TO_QT:.1f} qt)" if unit == "L" else ""
        return f"{str(data.get('system', '')).replace('_', ' ').capitalize()}: {amt} {unit}{extra}"
    if kind == Kind.spec and data.get("name"):
        rng = f"–{data['value_max']}" if data.get("value_max") is not None else ""
        return f"{data['name']}: {data.get('value')}{rng}"
    return ""


def page_for_entry(db: Session, entry_id: str, url: str) -> Page | None:
    if not entry_id.isdigit():
        return None
    e = db.get(Entry, int(entry_id))
    if e is None or e.status != EntryStatus.published or e.current_revision_id is None:
        return None  # never reveal pending/hidden content
    rev = db.get(EntryRevision, e.current_revision_id)
    data = rev.data
    summary = data.get("summary") or data.get("job") or _spec_line(e.kind, data) or e.title
    parts = [f"<h1>{escape(e.title)}</h1>"]
    if line := _spec_line(e.kind, data):
        parts.append(f"<p><strong>{escape(line)}</strong></p>")
    if data.get("summary"):
        parts.append(f"<p>{escape(data['summary'])}</p>")
    if data.get("tools"):
        parts.append("<h2>Tools</h2>" + _list(data["tools"]))
    if data.get("parts"):
        parts.append("<h2>Parts</h2>" + _list(data["parts"]))
    if data.get("steps"):
        parts.append("<h2>Steps</h2>" + _list([s.get("text", "") for s in data["steps"]], "ol"))
    desc = _clip(summary)
    return Page(title=f"{e.title} | {SITE}", description=desc, body="".join(parts),
                jsonld=_article(e.title, desc, url))  # fmt: skip


def page_for_vehicle(db: Session, vehicle_id: str, url: str) -> Page | None:
    if not vehicle_id.isdigit():
        return None
    v = db.get(Vehicle, int(vehicle_id))
    if v is None:
        return None
    label = vehicle_out(v).label
    counts = {name: fn(db, v) for name, fn in PROFILE_COUNTERS.items()}
    facts = [f"{n} {name}" for name, n in counts.items() if n]
    desc = _clip(f"{label}: recalls, technical service bulletins, owner complaints, trouble codes, "
                 f"repair guides, torque specs and labor times. Free.")  # fmt: skip
    body = f"<h1>{escape(label)}</h1><p>{escape(desc)}</p>" + _list(facts)
    return Page(
        title=f"{label} — recalls, TSBs & repair info | {SITE}", description=desc, body=body
    )


def page_for_codes_index(db: Session) -> Page:
    rows = db.scalars(select(Dtc).where(Dtc.make_id.is_(None)).order_by(Dtc.code)).all()
    links = "".join(
        f'<li><a href="/codes/{escape(d.code)}">{escape(d.code)} — {escape(d.title)}</a></li>'
        for d in rows
    )
    return Page(
        title=f"OBD-II trouble codes: meaning, causes & diagnosis | {SITE}",
        description="Free plain-English explanations of OBD-II trouble codes with symptoms, likely causes and step-by-step diagnosis.",
        body=f"<h1>OBD-II trouble codes</h1><ul>{links}</ul>",
    )


PRIVATE_PREFIXES = ("account", "mod", "login", "register", "garage", "entries/new", "forgot-password",
                    "reset-password", "verify-email")  # fmt: skip


def page_for_path(db: Session, path: str) -> Page:
    base = get_settings().public_base_url
    url = f"{base}/{path}".rstrip("/")
    segs = path.strip("/").split("/")
    page = None
    if segs[0] == "codes" and len(segs) == 1:
        page = page_for_codes_index(db)
    elif segs[0] == "codes" and len(segs) == 2:
        page = page_for_code(db, segs[1], url)
    elif segs[0] == "entries" and len(segs) == 2:
        page = page_for_entry(db, segs[1], url)
    elif segs[0] == "vehicle" and len(segs) == 2:
        page = page_for_vehicle(db, segs[1], url)
    if page is None:
        page = Page(title=f"{SITE} — free auto repair information")
        page.noindex = path.startswith(PRIVATE_PREFIXES) or (
            bool(path) and segs[0] in ("entries", "vehicle", "codes")
        )
    return page


def render(template: str, page: Page, path: str) -> str:
    base = get_settings().public_base_url
    canonical = f"{base}/{path}".rstrip("/") or base
    head = [
        f'<meta name="description" content="{escape(page.description)}" />',
        f'<link rel="canonical" href="{escape(canonical)}" />',
        f'<meta property="og:site_name" content="{SITE}" />',
        f'<meta property="og:title" content="{escape(page.title)}" />',
        f'<meta property="og:description" content="{escape(page.description)}" />',
        f'<meta property="og:url" content="{escape(canonical)}" />',
        '<meta property="og:type" content="article" />',
    ]
    if page.noindex:
        head.append('<meta name="robots" content="noindex" />')
    if code := get_settings().google_site_verification:
        head.append(f'<meta name="google-site-verification" content="{escape(code)}" />')
    if page.jsonld:
        data = json.dumps(page.jsonld, ensure_ascii=False).replace("</", "<\\/")
        head.append(f'<script type="application/ld+json">{data}</script>')
    html = template
    # Replace the default title/description from index.html.
    start, end = html.find("<title>"), html.find("</title>")
    if start != -1 and end != -1:
        html = html[:start] + f"<title>{escape(page.title)}</title>" + html[end + len("</title>") :]
    html = _drop_tag(html, '<meta name="description"')
    html = html.replace("</head>", "    " + "\n    ".join(head) + "\n  </head>", 1)
    if page.body:
        html = html.replace(
            '<div id="root"></div>', f'<div id="root"><main>{page.body}</main></div>', 1
        )
    return html


def _drop_tag(html: str, prefix: str) -> str:
    i = html.find(prefix)
    if i == -1:
        return html
    j = html.find(">", i)
    return html[:i] + html[j + 1 :]


def sitemap(db: Session) -> str:
    base = get_settings().public_base_url
    urls = [f"{base}/", f"{base}/codes"]
    urls += [
        f"{base}/codes/{c}"
        for c in db.scalars(select(Dtc.code).where(Dtc.make_id.is_(None)).order_by(Dtc.code))
    ]
    entries = db.execute(
        select(Entry.id, Entry.updated_at)
        .where(Entry.status == EntryStatus.published)
        .order_by(Entry.id)
        .limit(40000)
    ).all()
    vehicles = db.scalars(select(Vehicle.id).order_by(Vehicle.id).limit(5000)).all()
    items = [f"<url><loc>{escape(u)}</loc></url>" for u in urls]
    items += [
        f"<url><loc>{base}/entries/{i}</loc><lastmod>{u.date().isoformat()}</lastmod></url>"
        for i, u in entries
    ]
    items += [f"<url><loc>{base}/vehicle/{i}</loc></url>" for i in vehicles]
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(items)
        + "</urlset>\n"
    )


def robots() -> str:
    base = get_settings().public_base_url
    disallow = "".join(f"Disallow: /{p}\n" for p in ("api/", "account", "mod", "login", "register", "garage",
                                                      "entries/new", "search"))  # fmt: skip
    return f"User-agent: *\n{disallow}Allow: /\nSitemap: {base}/sitemap.xml\n"
