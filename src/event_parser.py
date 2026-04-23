"""
Parse events/<slug>.md into a structured dict.

Format:
    ---
    slug: 2026-06-personality-day
    date: 2026-06-06
    start_time: 14:00
    location: Zion
    min_attendees: 6
    host_contact: pastor_zion       # references people.yaml key
    invite_list: [donovan_smith, ...]  # optional; empty -> default_invite
    photo_path: assets/photos/june.jpg
    poll_until: 2026-06-06T18:00    # optional
    ---

    # Event title

    ## Headline
    <one-liner>

    ## About
    <paragraph(s)>

    ## Schedule
    | time | activity |

Everything after the frontmatter is the same format used by the flyer/brochure
builder so the brochure generator can consume the same file.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Event:
    slug: str
    title: str
    date: datetime.date
    start_time: str | None
    location: str
    min_attendees: int
    host_contact: str | None
    invite_list: list[str]
    photo_path: str | None
    poll_until: datetime.datetime | None
    headline: str
    about: str
    schedule: list[tuple[str, str]]
    source_path: Path
    raw_frontmatter: dict = field(default_factory=dict)


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def parse(path: str | Path) -> Event:
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(
            f"{path} has no YAML frontmatter — expected a leading --- ... --- block"
        )
    fm = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)

    def _required(key: str):
        if key not in fm:
            raise ValueError(f"{path}: frontmatter missing required field '{key}'")
        return fm[key]

    date = _required("date")
    if isinstance(date, str):
        date = datetime.date.fromisoformat(date)

    poll_until = fm.get("poll_until")
    if isinstance(poll_until, str):
        poll_until = datetime.datetime.fromisoformat(poll_until)

    title = _heading(body, "# ") or path.stem
    headline = _section(body, "Headline")
    about = _section(body, "About")
    schedule = _schedule(body)

    return Event(
        slug=_required("slug"),
        title=title,
        date=date,
        start_time=fm.get("start_time"),
        location=_required("location"),
        min_attendees=int(fm.get("min_attendees", 0)),
        host_contact=fm.get("host_contact"),
        invite_list=list(fm.get("invite_list") or []),
        photo_path=fm.get("photo_path"),
        poll_until=poll_until,
        headline=headline,
        about=about,
        schedule=schedule,
        source_path=path,
        raw_frontmatter=fm,
    )


def _heading(body: str, prefix: str) -> str:
    for line in body.splitlines():
        if line.startswith(prefix) and not line.startswith(prefix + "#"):
            return line[len(prefix):].strip()
    return ""


def _section(body: str, heading: str) -> str:
    """Return the text under `## <heading>` up to the next `## ` or end."""
    lines = body.splitlines()
    out: list[str] = []
    in_section = False
    for ln in lines:
        if ln.strip().lower() == f"## {heading.lower()}":
            in_section = True
            continue
        if in_section and ln.startswith("## "):
            break
        if in_section:
            out.append(ln)
    return "\n".join(out).strip()


def _schedule(body: str) -> list[tuple[str, str]]:
    in_sched = False
    rows: list[tuple[str, str]] = []
    for ln in body.splitlines():
        if ln.strip().lower() == "## schedule":
            in_sched = True
            continue
        if in_sched and ln.startswith("## "):
            break
        if not in_sched:
            continue
        m = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", ln)
        if m and "---" not in m.group(1) and m.group(1).lower() != "time":
            rows.append((m.group(1).strip(), m.group(2).strip()))
    return rows
