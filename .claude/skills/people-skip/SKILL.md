---
name: people-skip
description: Mark a person to be SKIPPED for a specific event or for the next event. Adds their key to the event's skip_list. Keeps their people.yaml entry intact. Use when the user says "Donny can't make it this month" / "skip Jane for June" / "don't invite X to the next one."
---

# people-skip

## When to invoke

- "Donny can't make it this time"
- "skip Jane for June"
- "don't invite the pastor to the cookout"
- "/people-skip donny next"
- "/people-skip jane 2026-06-personality-day"

## Arguments

- `<person>`: the person's `key` in `people.yaml` (e.g. `donny_smith`) OR
  a name that fuzzy-matches one entry. If ambiguous, ask.
- `<event>`:
  - A specific event slug (`2026-06-personality-day`)
  - Or `next` → apply to the most recent active event
  - Or `permanent` → flip their `default_invite` to `false` in people.yaml
  - Or `unskip <event>` → remove their key from that event's skip_list

## Flow

### Step 1 — resolve the person

If the user passed a key, look it up in `people.yaml`. If not found,
fuzzy-match by name. If multiple candidates, ask.

### Step 2 — resolve the event

- `next` → list active events (upcoming events whose date hasn't passed)
  and pick the nearest. Show it and confirm.
- Specific slug → verify the file exists.
- `permanent` → no event needed; confirm this is a durable change.

### Step 3 — apply the skip

**For a specific event:**

Read `events/<slug>.md` frontmatter. Add the person's key to `skip_list:`
(create the list if absent). Write the file back, preserving the rest
of the frontmatter formatting.

Show the before/after:

```
events/2026-06-personality-day.md:
  skip_list:
  -  (empty)
  +  - donny_smith    # Donny can't make it — added 2026-04-23
```

**For `permanent`:**

Edit `people.yaml` (via `secret.py` so it stays encrypted). Set
`default_invite: false` for that person. Confirm clearly that they
will no longer be auto-included in future events. Their entry stays
intact for reference / per-event manual invites.

**For `unskip`:**

Remove the person's key from the event's skip_list. Show the diff.

### Step 4 — confirm

Show a summary:

```
Donny Smith will NOT be invited to 2026-06-personality-day.
His people.yaml entry is unchanged; he'll be invited to future events
by default.
```

## Guardrails

- Never delete a person's people.yaml entry from this skill. Use
  `/people-remove` for that. Skip is reversible; removal is not.
- When skipping for `permanent`, warn the user and require explicit
  confirmation ("yes, skip permanently").
- Log every skip in the event state with timestamp + reason (if user
  gave one).
- If the named event has already had invites sent to this person,
  warn the user that the skip is retroactive and they may need to
  send a manual follow-up ("actually — never mind about the 6th").
