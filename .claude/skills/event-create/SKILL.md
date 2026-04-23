---
name: event-create
description: Create a new LYA event end-to-end from a conversation. Asks clarifying questions, drafts events/<slug>.md, sets up preflight checklist, creates Trello board + Google Sheet + brochure. Blocks at preflight gate before any invites go out. Use when the user says "let's plan the June cookout" / "create an event" / "set up the next gathering."
---

# event-create

## When to invoke

Any time the user signals they want to kick off a new event:
- "let's plan X"
- "set up the June event"
- "I want to do a new gathering on..."
- "create a new event for..."

## Flow

### Step 1 — gather the essentials conversationally

Ask questions one at a time if they're missing, NOT all at once. Required facts:
- **Slug** (auto-derive from date + title, e.g. `2026-06-personality-day`)
- **Date** (ISO format)
- **Start time**
- **Location** (name + host key from `people.yaml`)
- **Event title** (short, e.g. "Personality Day")
- **Headline** (one liner, used on brochure)
- **About** (2–4 sentence blurb)
- **Schedule** (time + activity rows, like the Excel source)
- **Min attendees** (default 6)
- **Invite list** — default to everyone in `people.yaml` with `default_invite: true`; let user add/remove
- **Preflight items** — default `[location_confirmed, date_confirmed]`; user can add more

Don't ask for fields the user has already stated. Re-read conversation history first.

### Step 2 — write events/<slug>.md

Use the YAML frontmatter format documented in `src/event_parser.py`. Body has
`# Title`, `## Headline`, `## About`, `## Schedule` sections.

Show the draft to the user for approval. Edit inline until they're happy.

### Step 3 — generate the brochure preview

Run:
```
python3 build.py --format brochure
```

If the event markdown refers to fields the current `build.py` / template
doesn't know about (e.g. new event-specific metadata), either extend the
template or skip the brochure step for this iteration.

Show the PDF path; invite the user to review it.

### Step 4 — preflight (DO NOT send anything yet)

Do NOT invoke `event-invite`. Explain to the user that the invite phase
is BLOCKED until preflight is complete, and list what preflight expects:

```
Preflight for 2026-06-personality-day:
  ☐ location_confirmed  → /event-confirm location
  ☐ date_confirmed      → /event-confirm date
```

Offer to run `/event-confirm location` right now if the user is ready.

### Step 5 — Trello + Sheet (gated on credentials)

If `.env` has Trello key/token and Google service account, call the
`orchestrate.py trello-create <slug>` and `orchestrate.py sheet-create <slug>`
primitives. Otherwise report "Trello and Google Sheet setup pending
credentials — skipping for now" and continue.

## Output artifacts

- `events/<slug>.md` — committed to repo
- `brochure.pdf` — regenerated; review before committing
- encrypted per-event state at `~/.config/event_planner/event-<slug>.age`
- Trello board URL (once creds are in)
- Google Sheet URL (once creds are in)

## Guardrails

- NEVER skip preflight. The only way past is an explicit
  `--override-preflight` flag passed by the user, which gets logged.
- NEVER draft or send invites inside this skill. That's `event-invite`'s job,
  gated by preflight.
- ALWAYS show the event markdown to the user for approval before writing it.
- For any content that would touch `people.yaml` (e.g. updating an invite list),
  use `/people-edit` — don't modify the file here directly.
