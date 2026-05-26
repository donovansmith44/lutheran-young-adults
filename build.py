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
        "gathering_label": "Our First Gathering",
        "tally_text": "tally.so/r/Ek8QeA",
        "qr_src": "assets/qr-rsvp.svg",
        "rsvp_url": RSVP_URL,
        "qr_out": ROOT / "assets" / "qr-rsvp.svg",
        "featured_index": 0,   # Personality Day
        "upcoming": (1, 3),    # America's 250th + Clippers Game
    },
    # Post-first-event variant: America's 250th becomes the next gathering,
    # Personality Day (now past) is dropped, Clippers moves up and the
    # September event joins the upcoming list. The QR points at a fresh
    # Tally form. Shares the poster template + stylesheet with "poster".
    "poster-next": {
        "template": ROOT / "templates" / "poster_template.html",
        "html_out": ROOT / "poster-next.html",
        "css_in": ROOT / "src" / "poster.css",
        "css_out": ROOT / "poster.css",
        "pdf_out": ROOT / "poster-next.pdf",
        "gathering_label": "Our Next Gathering",
        "tally_text": "tally.so/r/LZ64ej",
        "qr_src": "assets/qr-rsvp-next.svg",
        "rsvp_url": "https://tally.so/r/LZ64ej",
        "qr_out": ROOT / "assets" / "qr-rsvp-next.svg",
        "featured_index": 1,   # America's 250th
        "upcoming": (2, 4),    # Clippers Game + Community Service Day
        "abbrev_months": True, # "September" would otherwise crowd its title
        "tbd_time": ("Community Service",),  # September time not yet set
        "featured_itinerary": True,  # show America's 250th's short agenda
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


def _itinerary_time(t: str) -> str:
    """Compact, en-dashed time for a poster itinerary row. Falls back to a
    plain hyphen->en-dash swap for open-ended rows like "5:45 PM - whenever"
    -> "5:45 PM–whenever" so they read consistently with the closed ranges."""
    compact = _compact_time(t)
    if compact != t:
        return compact
    m = re.match(r"^(.*?)\s*-\s*(.*)$", t)
    return f"{m.group(1)}–{m.group(2)}" if m else t


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


_MONTH_ABBR = {
    "january": "Jan", "february": "Feb", "march": "Mar", "april": "Apr",
    "may": "May", "june": "Jun", "july": "Jul", "august": "Aug",
    "september": "Sep", "october": "Oct", "november": "Nov", "december": "Dec",
}


def _short_date(date: str) -> str:
    """Compact a long date for the upcoming list: "04 july" -> "Jul 4".
    Falls back to the title-cased raw date if it can't be parsed."""
    parts = date.split()
    if len(parts) == 2 and parts[0].lstrip("0").isdigit():
        day = parts[0].lstrip("0")
        mon = _MONTH_ABBR.get(parts[1].lower())
        if mon:
            return f"{mon} {day}"
    return date.title()


def _start_time(t: str) -> str:
    """Start clock time only, ":00" minutes dropped, AM/PM kept:
    "5:00 PM - 5:45 PM" -> "5 PM"; "7:05 PM - whenever" -> "7:05 PM";
    "11:30 AM - 12:00 PM" -> "11:30 AM"."""
    m = re.match(r"^(\d{1,2}:\d{2})\s*(AM|PM)?", t)
    if not m:
        return t
    start = m.group(1).replace(":00", "")
    ap = m.group(2) or ""
    return f"{start} {ap}".strip()


def poster_time_span(ev: dict) -> str:
    """Overall start–end for the featured event, e.g. "2:00 – 6:30 PM".
    Replaces the itemized itinerary on the poster with a single hours line."""
    times = ev.get("times") or []
    if not times:
        return ""
    m_start = re.match(r"^(\d{1,2}:\d{2})\s*(AM|PM)?", times[0][0])
    m_end = re.search(r"[-–]\s*(\d{1,2}:\d{2})\s*(AM|PM)?\s*$", times[-1][0])
    if not (m_start and m_end):
        return ""
    start, start_ap = m_start.group(1), m_start.group(2) or ""
    end, end_ap = m_end.group(1), m_end.group(2) or start_ap
    if start_ap and start_ap == end_ap:
        return f"{start}–{end} {end_ap}"
    return f"{start} {start_ap}–{end} {end_ap}".strip()


def render_poster_upcoming(upcoming: list) -> str:
    """Upcoming events for the poster's right column — each rendered like the
    featured event in the middle column: title, a "date · time · place" meta
    line, and its descriptive blurb."""
    items = []
    for ev in upcoming:
        is_tba = (not ev["title"]) or ev["title"].upper() == "TBD"
        title = "To be announced" if is_tba else ev["title"]
        short_date = _short_date(ev["date"]) if ev.get("date") else ""
        start_time = _start_time(ev["times"][0][0]) if ev.get("times") else ""
        place = "" if is_tba else (ev["location"] if ev.get("location") else "")
        if place == "TBD":
            place = "Location TBD"
        meta = " · ".join(p for p in [short_date, start_time, place] if p)
        blurb = ev.get("about") or ""
        blurb_html = f'<p class="up-blurb">{blurb}</p>' if blurb else ""
        items.append(
            f'<li class="up-item">'
            f'<div class="up-title">{title}</div>'
            f'<div class="up-meta">{meta}</div>'
            f'{blurb_html}'
            f'</li>'
        )
    return "\n".join(items)


def _event_time(ev: dict) -> str:
    """Time shown above the event name on a poster event card: the full
    span when both ends are real clock times ("2:00–6:30 PM"), otherwise
    just the start time ("5:00 PM") for events that run until "whenever"."""
    span = poster_time_span(ev)
    if span:
        return span
    times = ev.get("times") or []
    return _start_time(times[0][0]) if times else ""


def render_poster_event(ev: dict, callout: str = "", featured: bool = False,
                        abbrev_month: bool = False, time_tbd: bool = False,
                        show_itinerary: bool = False) -> str:
    """Brochure-style event card for the poster's middle/right columns:
    a big date paired with a location/time stack above the event name,
    a rule beneath the head, then the "what to expect" blurb (in place of
    the brochure's itinerary). `callout` is an optional emphasis line
    (e.g. the free-dinner note) shown only on the featured event.

    The featured card shows the full time span; upcoming cards use the
    compact start time. `abbrev_month` shortens the date's month to three
    letters ("September" -> "Sep") so a long month + long title still fit
    one event head (used on the post-first-event poster). `time_tbd` shows
    "Time TBD" for an event whose time isn't finalized yet. `show_itinerary`
    appends the event's (compacted) agenda rows beneath the blurb."""
    is_tba = (not ev.get("title")) or ev["title"].upper() == "TBD"
    title = "To be announced" if is_tba else ev["title"]
    location = "" if is_tba else (ev.get("location") or "")
    if location.upper() == "TBD":
        location = "Location TBD"
    times = ev.get("times") or []
    if time_tbd:
        time = "Time TBD"
    elif is_tba or not times:
        time = ""
    elif featured:
        time = _event_time(ev)
    else:
        time = _start_time(times[0][0])
    loc_html = f'<span class="event-location">{location}</span>' if location else ""
    time_html = f'<span class="event-time">{time}</span>' if time else ""
    callout_html = f'<div class="event-callout">{callout}</div>' if callout else ""
    blurb = ev.get("about") or ""
    blurb_html = f'<p class="event-blurb">{blurb}</p>' if blurb else ""
    itinerary_html = ""
    if show_itinerary and times and not is_tba:
        rows = "".join(
            f'<span class="t">{_itinerary_time(t)}</span><span class="a">{a}</span>'
            for t, a in times
        )
        itinerary_html = f'<div class="event-times">{rows}</div>'
    # Poster date: drop the leading zero ("01 August" -> "1 August") so the
    # day number stays compact and the right-aligned title keeps enough
    # width to sit on one line (e.g. "Clippers Game"). Optionally abbreviate
    # the month so a long month doesn't crowd the title off the head.
    parts = ev.get("date", "").split(None, 1)
    if len(parts) == 2:
        num = parts[0].lstrip("0") or parts[0]
        mon = _MONTH_ABBR.get(parts[1].lower(), parts[1].title()) if abbrev_month else parts[1]
        date_html = f'<span class="d-num">{num}</span><span class="d-mo">{mon}</span>'
    else:
        date_html = f'<span class="d-num">{ev.get("date", "")}</span>'
    return (
        '<section class="event">'
        '<div class="event-head">'
        f'<div class="date">{date_html}</div>'
        f'<div class="title-line">{loc_html}{time_html}{title}</div>'
        '</div>'
        f'{callout_html}'
        f'{blurb_html}'
        f'{itinerary_html}'
        '</section>'
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

    # Regenerate the RSVP QR code every build so swapping the URL just works.
    # Each format may point at its own RSVP target / QR file (the post-first-
    # event poster uses a different Tally form); defaults keep the shared one.
    rsvp_url = cfg.get("rsvp_url", RSVP_URL)
    qr_out = cfg.get("qr_out", QR_OUT)
    qr_out.parent.mkdir(parents=True, exist_ok=True)
    segno.make(rsvp_url, error="m").save(
        str(qr_out), kind="svg", scale=10, border=0,
        dark="#01404f", light=None, omitsize=True,
    )
    print(f"wrote {qr_out.relative_to(ROOT)}")

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

    # Poster pulls its featured ("next") event and a slice of upcoming
    # events by index (configurable per format), and pairs the featured one
    # with any hardcoded hero copy (e.g. the free-dinner callout) keyed off
    # its title. Indices run against the full event list, not the --max slice.
    all_events = data["events"]
    featured_index = cfg.get("featured_index", 0)
    up_start, up_end = cfg.get("upcoming", (1, 3))
    poster_ev = all_events[featured_index] if len(all_events) > featured_index else None
    upcoming_events = all_events[up_start:up_end]
    poster_hero = POSTER_HERO.get(poster_ev["title"], {}) if poster_ev else {}
    poster_loc_line = poster_ev["location"] if (poster_ev and poster_ev["location"] and poster_ev["location"] != "TBD") else ""
    # Schedule-column event head: day-of-week + long date ("Saturday", "20 June").
    poster_day = (poster_ev.get("day") or "Saturday") if poster_ev else ""
    poster_date_long = poster_ev["date"].title() if (poster_ev and poster_ev["date"]) else ""
    # Featured-event emphasis line (free-dinner callout) — only the
    # inaugural gathering carries one, sourced from POSTER_HERO.
    poster_callout = " · ".join(
        p for p in [poster_hero.get("callout_headline", ""), poster_hero.get("callout_sub", "")] if p
    ) if poster_ev else ""
    abbrev = cfg.get("abbrev_months", False)
    tbd_titles = set(cfg.get("tbd_time", ()))

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
        .replace("{{EVENT_DAY}}", poster_day)
        .replace("{{EVENT_DATE_LONG}}", poster_date_long)
        .replace("{{EVENT_TIME_SPAN}}", poster_time_span(poster_ev) if poster_ev else "")
        .replace("{{SCRIPTURE_PULLQUOTE}}", poster_hero.get("scripture", ""))
        .replace("{{SCRIPTURE_CITE_POSTER}}", poster_hero.get("scripture_cite", ""))
        .replace("{{CALLOUT_EYEBROW}}", poster_hero.get("callout_eyebrow", ""))
        .replace("{{CALLOUT_HEADLINE}}", poster_hero.get("callout_headline", ""))
        .replace("{{CALLOUT_SUB}}", poster_hero.get("callout_sub", ""))
        .replace("{{SCHEDULE_ROWS_POSTER}}", render_poster_schedule(poster_ev) if poster_ev else "")
        .replace("{{FEATURED_EVENT}}", render_poster_event(
            poster_ev, poster_callout, featured=True, abbrev_month=abbrev,
            time_tbd=poster_ev["title"] in tbd_titles,
            show_itinerary=cfg.get("featured_itinerary", False)) if poster_ev else "")
        .replace("{{UPCOMING_EVENTS}}", "\n".join(
            render_poster_event(ev, abbrev_month=abbrev, time_tbd=ev["title"] in tbd_titles)
            for ev in upcoming_events))
        .replace("{{GATHERING_LABEL}}", cfg.get("gathering_label", ""))
        .replace("{{TALLY_TEXT}}", cfg.get("tally_text", ""))
        .replace("{{QR_SRC}}", cfg.get("qr_src", "assets/qr-rsvp.svg"))
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
