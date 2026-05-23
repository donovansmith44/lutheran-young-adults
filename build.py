#!/usr/bin/env python3
"""
Markdown -> Flyer PDF build script.

Reads lya_event_series.md, parses title/subtitle/scripture/mission/events,
renders them into templates/flyer_template.html, builds Tailwind CSS,
and writes flyer.pdf.

Usage:
    python3 build.py              # default: first 3 events
    python3 build.py --max 7      # include up to 7 events
    python3 build.py --all        # include all events
"""

import argparse
import pathlib
import re
import subprocess
import sys
import segno
import weasyprint

ROOT = pathlib.Path(__file__).parent
MD = ROOT / "lya_event_series.md"
TAILWIND = next(
    (p for p in (ROOT / "tailwindcss.exe", ROOT / "tailwindcss") if p.exists()),
    ROOT / "tailwindcss",
)
QR_OUT = ROOT / "assets" / "qr-rsvp.svg"

# Where the QR code sends people. We use a permanent GitHub Pages URL
# (rsvp.html in this repo, deployed via Pages) as an indirection layer:
# the printed QR encodes this URL forever, and the *contents* of rsvp.html
# can be edited later to redirect to a Tally form / Partiful / etc.
# without invalidating already-printed brochures.
RSVP_URL = "https://donovansmith44.github.io/lutheran-young-adults/rsvp.html"

FORMATS = {
    "flyer": {
        "template": ROOT / "templates" / "flyer_template.html",
        "html_out": ROOT / "flyer.html",
        "css_in": ROOT / "src" / "input.css",
        "css_out": ROOT / "flyer.css",
        "pdf_out": ROOT / "flyer.pdf",
    },
    "brochure": {
        "template": ROOT / "templates" / "brochure_template.html",
        "html_out": ROOT / "brochure.html",
        "css_in": ROOT / "src" / "brochure.css",
        "css_out": ROOT / "brochure.css",
        "pdf_out": ROOT / "brochure.pdf",
    },
    "poster": {
        "template": ROOT / "templates" / "poster_template.html",
        "html_out": ROOT / "poster.html",
        "css_in": ROOT / "src" / "poster.css",
        "css_out": ROOT / "poster.css",
        "pdf_out": ROOT / "poster.pdf",
    },
}


def parse_markdown(text: str) -> dict:
    """Parse the event-series markdown into a structured dict."""
    lines = text.splitlines()

    title = ""
    subtitle = ""
    scripture_text = ""
    scripture_cite = ""
    salutation = ""
    mission_paragraphs = []
    events = []

    # --- top-of-doc metadata ---
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith("# ") and not title:
            title = ln[2:].strip()
        elif ln.startswith("## ") and not subtitle and not ln.lower().startswith("## schedule"):
            subtitle = ln[3:].strip()
        elif ln.startswith("> "):
            # blockquote — scripture. Take the whole quote (may span lines).
            quote = ln[2:].strip()
            j = i + 1
            while j < len(lines) and lines[j].startswith("> "):
                quote += " " + lines[j][2:].strip()
                j += 1
            # split quote from citation: "...drawing near."* (Hbr. 10:24-25, ESV)
            m = re.match(r'^\*?"?(.+?)"?\*?\s*\((.+?)\)\s*$', quote)
            if m:
                scripture_text = m.group(1).strip().strip('*').strip('"')
                scripture_cite = m.group(2).strip()
            else:
                scripture_text = quote
            i = j - 1
        elif ln.startswith("### ") and not salutation and "brothers and sisters" in ln.lower():
            salutation = ln[4:].strip().rstrip(",")
            # collect mission paragraphs until next separator
            j = i + 1
            current = []
            while j < len(lines):
                pl = lines[j].rstrip()
                if pl.startswith("---") or pl.startswith("## "):
                    break
                if pl.strip() == "":
                    if current:
                        mission_paragraphs.append(" ".join(current).strip())
                        current = []
                else:
                    current.append(pl.strip())
                j += 1
            if current:
                mission_paragraphs.append(" ".join(current).strip())
            i = j - 1
        elif ln.lower().startswith("## schedule"):
            # --- events block ---
            j = i + 1
            while j < len(lines):
                pl = lines[j].rstrip()
                m = re.match(r"^### (.+?) — (.+?)$", pl)
                if m:
                    date_raw = m.group(1).strip()
                    event_title = m.group(2).strip()
                    # split date from optional " (Saturday)" suffix
                    dm = re.match(r"^(.+?)(?:\s*\((.+?)\))?$", date_raw)
                    date = dm.group(1).strip() if dm else date_raw
                    day = dm.group(2).strip() if dm and dm.group(2) else ""
                    ev = {
                        "date": date,
                        "day": day,
                        "title": event_title,
                        "location": "",
                        "headline": "",
                        "about": "",
                        "times": [],
                        "note": "",
                    }
                    k = j + 1
                    while k < len(lines):
                        nl = lines[k].rstrip()
                        if nl.startswith("### ") or nl.startswith("## ") or nl.startswith("---"):
                            break
                        lm = re.match(r"^\*\*Location:\*\*\s*(.+)$", nl)
                        if lm:
                            ev["location"] = lm.group(1).strip()
                        hm = re.match(r"^\*\*Headline:\*\*\s*(.+)$", nl)
                        if hm:
                            ev["headline"] = hm.group(1).strip()
                        am = re.match(r"^\*\*About:\*\*\s*(.+)$", nl)
                        if am:
                            ev["about"] = am.group(1).strip()
                        # table row: | time | activity |
                        tm = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", nl)
                        if tm and tm.group(1).lower() != "time" and "---" not in tm.group(1):
                            ev["times"].append((tm.group(1).strip(), tm.group(2).strip()))
                        # italic note
                        nm = re.match(r"^\*(.+)\*$", nl)
                        if nm:
                            ev["note"] = nm.group(1).strip()
                        k += 1
                    events.append(ev)
                    j = k
                else:
                    j += 1
            break
        i += 1

    return {
        "title": title,
        "subtitle": subtitle,
        "scripture": scripture_text,
        "scripture_cite": scripture_cite,
        "salutation": salutation + ",",
        "mission": mission_paragraphs,
        "events": events,
    }


def _date_html(ev: dict) -> str:
    parts = ev["date"].split(None, 1)
    if len(parts) == 2:
        return f'<span class="d-num">{parts[0]}</span><span class="d-mo">{parts[1]}</span>'
    return f'<span class="d-num">{ev["date"]}</span>'


def _schedule_event_html(ev: dict) -> str:
    is_tbd = not ev["times"] and ev["title"].upper() == "TBD"
    cls = "event event-tbd" if is_tbd else "event"
    day_html = f'<span class="day-suffix">· {ev["day"]}</span>' if ev["day"] else ""
    if ev["location"]:
        title_line = (
            f'<span class="event-location">{ev["location"]}</span>'
            f'{ev["title"]}'
        )
    else:
        title_line = ev["title"]
    times_html = ""
    if ev["times"]:
        items = "\n".join(
            f'<li><span class="t">{t}</span><span class="a">{a}</span></li>'
            for t, a in ev["times"]
        )
        times_html = f'<ul class="times">{items}</ul>'
    return (
        f'<section class="{cls}">'
        f'<div class="event-head">'
        f'<div class="date">{_date_html(ev)}{day_html}</div>'
        f'<div class="title-line">{title_line}</div>'
        f'</div>'
        f'{times_html}'
        f'</section>'
    )


def _about_event_html(ev: dict) -> str:
    headline_html = f'<p class="about-headline">{ev["headline"]}</p>' if ev["headline"] else ""
    blurb_html = f'<p class="about-blurb">{ev["about"]}</p>' if ev["about"] else ""
    cls = "about-event about-event--full" if (ev["headline"] or ev["about"]) else "about-event"
    return (
        f'<section class="{cls}">'
        f'<h3 class="about-title">{ev["title"]}</h3>'
        f'{headline_html}'
        f'{blurb_html}'
        f'</section>'
    )


def render_events_schedule(events: list) -> str:
    """Flyer-style stacked schedule list (used by the flyer template)."""
    return "\n".join(_schedule_event_html(ev) for ev in events)


def _compact_time(t: str) -> str:
    """Compress "2:00 PM - 2:30 PM" -> "2:00–2:30 PM" so each row fits a
    narrow time column at distance-readable type sizes."""
    m = re.match(r"^(\d{1,2}:\d{2})\s*(AM|PM)?\s*[-–]\s*(\d{1,2}:\d{2})\s*(AM|PM)?$", t)
    if not m:
        return t
    start, start_ap, end, end_ap = m.group(1), m.group(2), m.group(3), m.group(4)
    ap = end_ap or start_ap or ""
    return f"{start}–{end} {ap}".strip()


def _strip_time(t: str) -> str:
    """Compact start-only time for the poster's schedule strip:
    "2:00 PM - 2:30 PM" -> "2:00 PM". The strip is supplementary info,
    not the main event, so end times can be inferred from the next row."""
    m = re.match(r"^(\d{1,2}:\d{2})\s*(AM|PM)?\s*[-–]\s*\d{1,2}:\d{2}\s*(AM|PM)?$", t)
    if not m:
        return t
    start, start_ap, end_ap = m.group(1), m.group(2), m.group(3)
    ap = start_ap or end_ap or ""
    return f"{start} {ap}".strip()


def render_poster_schedule(ev: dict) -> str:
    """Schedule rows for the poster's left-column agenda — full time
    ranges (compacted from "2:00 PM - 2:30 PM" to "2:00–2:30 PM") and
    the full activity label from the markdown.
    """
    return "\n".join(
        f'<li><span class="t">{_compact_time(t)}</span>'
        f'<span class="a">{a}</span></li>'
        for t, a in ev["times"]
    )


# Poster-specific copy that doesn't belong in the events markdown.
# Keyed by event title — this is the inaugural-gathering framing and
# the free-dinner callout, both intentionally loud on the poster.
POSTER_HERO = {
    "Personality Day": {
        "eyebrow": "Our First Gathering",
        "title_big": "Personality Day",
        "scripture": (
            "Behold, how good and how pleasant it is for brethren "
            "to dwell together in unity!"
        ),
        "scripture_cite": "Psalm 133",
        "callout_eyebrow": "Included with the event",
        "callout_headline": "Free Dinner",
        "callout_sub": "catered by Zupas",
    },
}


def poster_meta_line(ev: dict) -> str:
    """One-line event meta below the hero title:
    "Saturday · 20 June · 2 – 6:30 PM · Zion".

    Folds day-of-week, date, time span, and venue into a single
    horizontally-balanced strip so the hero zone stays 3 lines tall
    (eyebrow + title + meta) instead of 4.
    """
    day = ev.get("day") or "Saturday"
    date = ev.get("date", "")
    location = ev.get("location") or ""
    if location.upper() == "TBD":
        location = ""
    times = ev.get("times") or []
    span = ""
    if times:
        first_t = times[0][0]
        last_t = times[-1][0]
        m_start = re.match(r"^(\d{1,2}:\d{2})", first_t)
        m_end = re.search(r"[-–]\s*(\d{1,2}:\d{2})\s*(AM|PM)?$", last_t)
        if m_start and m_end:
            ap = m_end.group(2) or "PM"
            # drop ":00" minutes for compactness in the hero strip
            start_t = m_start.group(1).replace(":00", "")
            end_t = m_end.group(1)
            span = f"{start_t} – {end_t} {ap}"
    parts = [p for p in [day, date.title() if date else "", span, location] if p]
    return " · ".join(parts)


def render_inside_rows(events: list) -> str:
    """Paired schedule+about table rows for the brochure inside face.

    Each event becomes one <tr> with two <td>s so the schedule entry
    and the about description share a row height and align.
    """
    rows = []
    for ev in events:
        rows.append(
            '<tr class="row-event">'
            f'<td class="cell cell-sched cell-event">{_schedule_event_html(ev)}</td>'
            f'<td class="cell cell-about cell-event">{_about_event_html(ev)}</td>'
            '</tr>'
        )
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=list(FORMATS), default="flyer")
    ap.add_argument("--max", type=int, default=3, help="max events (flyer only)")
    ap.add_argument("--all", action="store_true", help="include all events")
    args = ap.parse_args()

    cfg = FORMATS[args.format]
    expected_pages = 2 if args.format == "brochure" else 1

    md = MD.read_text(encoding="utf-8")
    data = parse_markdown(md)

    events = data["events"] if args.all else data["events"][: args.max]

    # Regenerate the RSVP QR code every build so swapping RSVP_URL just works.
    QR_OUT.parent.mkdir(parents=True, exist_ok=True)
    segno.make(RSVP_URL, error="m").save(
        str(QR_OUT), kind="svg", scale=10, border=0,
        dark="#01404f", light=None, omitsize=True,
    )
    print(f"wrote {QR_OUT.relative_to(ROOT)}")

    template = cfg["template"].read_text(encoding="utf-8")
    mission_html = "\n".join(f"<p>{p}</p>" for p in data["mission"])
    # front-of-brochure gets a lightly condensed mission (same text for now)
    mission_front_html = mission_html

    # Front-cover title: break after the first word so "Lutheran" sits on its
    # own line and the remaining words stay glued together as a non-breaking
    # unit (prevents a mid-phrase wrap like "YOUNG" / "ADULTS" on the narrow
    # 3.5" front panel).
    title_words = data["title"].upper().split()
    if len(title_words) >= 2:
        title_upper_cover = title_words[0] + "<br>" + "&nbsp;".join(title_words[1:])
    else:
        title_upper_cover = data["title"].upper()

    # Poster pulls the first (next-up) event and pairs it with hardcoded
    # hero copy (eyebrow framing, scripture pullquote, free-dinner callout)
    # that doesn't belong in the recurring events markdown.
    poster_ev = events[0] if events else None
    poster_hero = POSTER_HERO.get(poster_ev["title"], {}) if poster_ev else {}
    poster_loc_line = poster_ev["location"] if (poster_ev and poster_ev["location"] and poster_ev["location"] != "TBD") else ""

    html = (
        template
        .replace("{{TITLE}}", data["title"])
        .replace("{{TITLE_UPPER}}", title_upper_cover)
        .replace("{{GROUP_NAME_UPPER}}", data["title"])
        .replace("{{SUBTITLE}}", data["subtitle"])
        .replace("{{SCRIPTURE}}", data["scripture"])
        .replace("{{SCRIPTURE_CITE}}", data["scripture_cite"])
        .replace("{{SALUTATION}}", data["salutation"])
        .replace("{{MISSION_FRONT}}", mission_front_html)
        .replace("{{MISSION}}", mission_html)
        .replace("{{EVENTS}}", render_events_schedule(events))
        .replace("{{INSIDE_ROWS}}", render_inside_rows(events))
        .replace("{{EYEBROW}}", poster_hero.get("eyebrow", ""))
        .replace("{{EVENT_TITLE_BIG}}", poster_hero.get("title_big", poster_ev["title"] if poster_ev else ""))
        .replace("{{EVENT_META_LINE}}", poster_meta_line(poster_ev) if poster_ev else "")
        .replace("{{EVENT_LOCATION_LINE}}", poster_loc_line)
        .replace("{{SCRIPTURE_PULLQUOTE}}", poster_hero.get("scripture", ""))
        .replace("{{SCRIPTURE_CITE_POSTER}}", poster_hero.get("scripture_cite", ""))
        .replace("{{CALLOUT_EYEBROW}}", poster_hero.get("callout_eyebrow", ""))
        .replace("{{CALLOUT_HEADLINE}}", poster_hero.get("callout_headline", ""))
        .replace("{{CALLOUT_SUB}}", poster_hero.get("callout_sub", ""))
        .replace("{{SCHEDULE_ROWS_POSTER}}", render_poster_schedule(poster_ev) if poster_ev else "")
        .replace("{{ABOUT_HEADLINE}}", poster_ev["headline"] if poster_ev else "")
        .replace("{{ABOUT_BLURB}}", poster_ev["about"] if poster_ev else "")
    )
    cfg["html_out"].write_text(html, encoding="utf-8")
    print(f"wrote {cfg['html_out'].name}")

    if TAILWIND.exists():
        subprocess.run(
            [str(TAILWIND), "-i", str(cfg["css_in"]), "-o", str(cfg["css_out"]), "--minify"],
            check=True, cwd=ROOT,
        )
        print(f"built {cfg['css_out'].name}")

    doc = weasyprint.HTML(str(cfg["html_out"]), base_url=str(ROOT)).render()
    doc.write_pdf(str(cfg["pdf_out"]))
    print(f"rendered {cfg['pdf_out'].name} ({len(doc.pages)} page{'s' if len(doc.pages) != 1 else ''})")

    if len(doc.pages) != expected_pages:
        print(f"  WARNING: expected {expected_pages} page(s), got {len(doc.pages)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
