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

import weasyprint

ROOT = pathlib.Path(__file__).parent
MD = ROOT / "lya_event_series.md"
TAILWIND = ROOT / "tailwindcss"

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


def render_events_schedule(events: list) -> str:
    """Left (schedule) panel: date + event name + times."""
    html = []
    for ev in events:
        is_tbd = not ev["times"] and ev["title"].upper() == "TBD"
        cls = "event event-tbd" if is_tbd else "event"
        day_html = f'<span class="day-suffix">· {ev["day"]}</span>' if ev["day"] else ""
        times_html = ""
        if ev["times"]:
            items = "\n".join(
                f'<li><span class="t">{t}</span><span class="a">{a}</span></li>'
                for t, a in ev["times"]
            )
            times_html = f'<ul class="times">{items}</ul>'
        html.append(
            f'<section class="{cls}">'
            f'<div class="event-head">'
            f'<div class="date">{_date_html(ev)}{day_html}</div>'
            f'<div class="title-line">{ev["title"]}</div>'
            f'</div>'
            f'{times_html}'
            f'</section>'
        )
    return "\n".join(html)


def render_events_about(events: list) -> str:
    """Middle (about) panel: event name + location + note."""
    html = []
    for ev in events:
        if not ev["times"] and ev["title"].upper() == "TBD":
            continue
        loc = ev["location"] if ev["location"] and ev["location"] != "TBD" else ""
        loc_html = f'<p class="about-location">{loc}</p>' if loc else ""
        note_html = f'<p class="about-note">{ev["note"]}</p>' if ev["note"] else ""
        html.append(
            f'<section class="about-event">'
            f'<div class="about-date">{_date_html(ev)}</div>'
            f'<h3 class="about-title">{ev["title"]}</h3>'
            f'{loc_html}'
            f'{note_html}'
            f'</section>'
        )
    return "\n".join(html)


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

    template = cfg["template"].read_text(encoding="utf-8")
    mission_html = "\n".join(f"<p>{p}</p>" for p in data["mission"])
    # front-of-brochure gets a lightly condensed mission (same text for now)
    mission_front_html = mission_html

    html = (
        template
        .replace("{{TITLE}}", data["title"])
        .replace("{{TITLE_UPPER}}", data["title"].upper())
        .replace("{{SUBTITLE}}", data["subtitle"])
        .replace("{{SCRIPTURE}}", data["scripture"])
        .replace("{{SCRIPTURE_CITE}}", data["scripture_cite"])
        .replace("{{SALUTATION}}", data["salutation"])
        .replace("{{MISSION_FRONT}}", mission_front_html)
        .replace("{{MISSION}}", mission_html)
        .replace("{{EVENTS}}", render_events_schedule(events))
        .replace("{{EVENTS_SCHEDULE}}", render_events_schedule(events))
        .replace("{{EVENTS_ABOUT}}", render_events_about(events))
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
        print(f"  ⚠ expected {expected_pages} page(s), got {len(doc.pages)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
