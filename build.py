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
TEMPLATE = ROOT / "templates" / "flyer_template.html"
HTML_OUT = ROOT / "flyer.html"
CSS_IN = ROOT / "src" / "input.css"
CSS_OUT = ROOT / "flyer.css"
PDF_OUT = ROOT / "flyer.pdf"
TAILWIND = ROOT / "tailwindcss"


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


def render_events(events: list) -> str:
    html = []
    for ev in events:
        is_tbd = not ev["times"] and ev["title"].upper() == "TBD"
        cls = "event event-tbd" if is_tbd else "event"
        day_html = f' <span class="day">· {ev["day"]}</span>' if ev["day"] else ""
        loc_html = f'<span class="loc">at {ev["location"]}</span>' if ev["location"] and ev["location"] != "TBD" else ""
        times_html = ""
        if ev["times"]:
            items = "\n".join(
                f'<li><span class="t">{t}</span><span class="dots"></span><span class="a">{a}</span></li>'
                for t, a in ev["times"]
            )
            times_html = f'<ul class="times">{items}</ul>'
        note_html = f'<p class="note">{ev["note"]}</p>' if ev["note"] else ""
        html.append(
            f'<section class="{cls}">'
            f'<div class="event-head">'
            f'<span class="date">{ev["date"]}{day_html}</span>'
            f'<span class="title">{ev["title"]}</span>'
            f'{loc_html}'
            f'</div>'
            f'{times_html}'
            f'{note_html}'
            f'</section>'
        )
    return "\n".join(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=3, help="max number of events to include")
    ap.add_argument("--all", action="store_true", help="include all events")
    args = ap.parse_args()

    md = MD.read_text(encoding="utf-8")
    data = parse_markdown(md)

    events = data["events"] if args.all else data["events"][: args.max]

    template = TEMPLATE.read_text(encoding="utf-8")
    mission_html = "\n".join(f"<p>{p}</p>" for p in data["mission"])

    html = (
        template
        .replace("{{TITLE}}", data["title"])
        .replace("{{SUBTITLE}}", data["subtitle"])
        .replace("{{SCRIPTURE}}", data["scripture"])
        .replace("{{SCRIPTURE_CITE}}", data["scripture_cite"])
        .replace("{{SALUTATION}}", data["salutation"])
        .replace("{{MISSION}}", mission_html)
        .replace("{{EVENTS}}", render_events(events))
    )
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"wrote {HTML_OUT.name}")

    if TAILWIND.exists():
        subprocess.run(
            [str(TAILWIND), "-i", str(CSS_IN), "-o", str(CSS_OUT), "--minify"],
            check=True, cwd=ROOT,
        )
        print(f"built {CSS_OUT.name}")

    doc = weasyprint.HTML(str(HTML_OUT), base_url=str(ROOT)).render()
    doc.write_pdf(str(PDF_OUT))
    print(f"rendered {PDF_OUT.name} ({len(doc.pages)} page{'s' if len(doc.pages) != 1 else ''})")

    if len(doc.pages) > 1:
        print(f"  ⚠ flyer overflowed to {len(doc.pages)} pages — consider --max with a smaller value")
        sys.exit(1)


if __name__ == "__main__":
    main()
