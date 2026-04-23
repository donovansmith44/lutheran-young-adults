---
name: event-watch
description: Run a cross-cutting health check on an event — reads preflight state, RSVP log, Trello board, Google Sheet, and deadlines; produces a structured risk report with suggested actions (push to pending, start cancellation, etc.). Can run once or loop on an interval with desktop notifications.
---

# event-watch

## When to invoke

- "how's the June event looking?"
- "is the cookout at risk?"
- "watch the July event for changes"
- "/event-watch 2026-06-personality-day"

## Arguments

- `<slug>`: event slug
- `--loop [INTERVAL]`: if present, run continuously; default interval 15 min
- `--until <datetime>`: auto-terminate at this time (defaults to event end)
- `--notify`: fire desktop notifications on state change (default: on for --loop)

## Flow

### Step 1 — gather inputs

In parallel:
- Event frontmatter from `events/<slug>.md` (date, min_attendees, preflight)
- Encrypted per-event state `~/.config/event_planner/event-<slug>.age`
  (preflight confirmations, outbound log, RSVP log)
- Trello board state via `orchestrate.py trello-board <slug>` (list positions,
  assignees, due dates, overdue cards)
- Google Sheet state via `orchestrate.py sheet-read <slug>` (claimed rows)

### Step 2 — compute risk signals

- **Preflight incomplete?** If any preflight item is not `confirmed` and
  event is within T-14 days → HIGH RISK
- **Overdue cards?** Any card with due date in past and not in "Done" list
  → count + list them
- **RSVP shortfall?** `coming` count vs `min_attendees`, weighted by days
  remaining:
  - T-14+ days, coming < 50% of min → LOW risk (early, still time)
  - T-7 days, coming < min → MEDIUM
  - T-3 days, coming < min → HIGH
- **Unclaimed pullable tasks with approaching deadlines** → list them
- **Pending invitees** with no reply → count; flag if T-7 days
- **Ambiguous status** (manual override, questions in reply log) → surface

### Step 3 — produce risk report

Example output:

```
EVENT: 2026-06-personality-day — Personality Day at Zion
DATE:  2026-06-06 (14 days out)
RISK:  MEDIUM

PREFLIGHT
  ✓ location_confirmed   (confirmed 2026-04-24 via email)
  ✗ date_confirmed        (not yet — run /event-confirm date)

RSVPs (6 minimum)
  coming:  3    ⚠ below minimum (T-14 days)
  maybe:   2
  pending: 2
  declined: 1

TRELLO
  ⚠ create_brochure — overdue by 4 days (was due T-28)
  ✓ food_signup_list — in progress (2/5 items claimed)
  ○ advertise_congregation_a — due in 3 days

SUGGESTIONS
  1. run /event-confirm date (preflight blocking)
  2. run /event-remind to push the 2 pending invitees
  3. nudge claims on food_signup_list (3 items still open)

You can run /event-cancel anytime if you want to call it; only the
accepted + maybe folks (5 people) would get the message.
```

### Step 4 — optional loop mode

If `--loop`, sleep for INTERVAL, repeat. On any state change vs previous
iteration (new RSVP, new claim, overdue → done), fire desktop
notification via `notify-send` (Linux) or `osascript` (macOS). Exit
gracefully on SIGINT or when `--until` is reached.

### Step 5 — optional Trello board comment

If any risk level is MEDIUM or HIGH, offer to post a card comment on
the event's epic card summarizing the report. Requires user approval.

## Guardrails

- This skill is READ-ONLY for shared state (Trello, Sheet, event state).
  It never modifies anything. Suggestions are human-decisions.
- NEVER auto-send reminders or cancellations. Those are separate skills
  behind their own approval gates.
- Loop mode writes nothing to disk except the local notification cache
  (to avoid duplicate notifications for the same state).
- If the orchestrator can't reach Trello or Sheets, surface the failure
  clearly and fall back to reporting only what's available locally —
  don't pretend everything is fine when data is stale.
