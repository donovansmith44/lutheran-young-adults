---
name: event-confirm
description: Confirm a single preflight item for an event (location, date, budget, etc.). Drafts the confirmation message to the right POC via their preferred channel (email/SMS), sends on approval, then logs the response as evidence in the encrypted per-event state. Unlocks the preflight gate for event-invite.
---

# event-confirm

## When to invoke

User says any of:
- "confirm the location for June"
- "check with Pastor about Zion"
- "get date locked in with Donny"
- "/event-confirm location 2026-06-personality-day"

## Arguments

- `<item>`: which preflight item. Common: `location`, `date`, `budget`,
  `catering`. Matches the entries in the event's frontmatter `preflight:` list.
- `<slug>`: event slug. If omitted and there's exactly one active event,
  infer it; otherwise ask.

## Flow

### Step 1 — load context

- Read `events/<slug>.md` frontmatter
- Identify the POC:
  - For `location_confirmed`: host_contact field in the frontmatter (references people.yaml key)
  - For `date_confirmed`: host_contact + any co-organizers the user flagged
  - Other items: ask which person is responsible if not obvious
- Read that person's entry in `people.yaml` → get preferred_channel

### Step 2 — handle in-person / offline contacts

If the POC's `preferred_channel` is `in_person` or `phone_call`, DO NOT draft
a message. Instead:

1. Surface a reminder to the user: "Pastor prefers phone — call him at
   <number> to confirm the fellowship hall for June 6"
2. If `relay_via` is set on the POC, offer to draft a message to the relay
   asking THEM to pass along the confirmation request
3. Wait for the user to come back with the response (from their
   in-person/phone conversation) and log it (Step 4)

### Step 3 — draft + send (for sms / email contacts)

Draft the confirmation message in-chat. Keep it:
- Direct, one sentence of context + one clear question
- In the voice from `voice.md`, adjusted per recipient's `style_samples`
- Brief enough that the reply is unambiguous ("yes" or "need to change X")

Example draft for location_confirmed (email to pastor):

> Pastor, confirming for June 6 — 2:00–6:30 PM in the fellowship hall
> for Lutheran Young Adults. Good to go?

Show draft. User approves / edits / skips. On approval, invoke the
relevant primitive:

- `preferred_channel: email` → `orchestrate.py email-send --to <addr> --subject ... --body ...`
- `preferred_channel: sms`   → `orchestrate.py sms-send --to <phone> --body ...`

If credentials aren't set, print the message to terminal and instruct the
user to send it manually this one time — offer to log the response afterward.

### Step 4 — log the response

Wait for the user to paste / describe the reply. Then stamp the preflight
item as confirmed in the per-event encrypted state:

```yaml
# ~/.config/event_planner/event-<slug>.age
preflight:
  location_confirmed:
    status: confirmed
    confirmed_at: 2026-04-24T09:14
    channel: email
    poc_key: pastor_zion
    verbatim: "Yes, fellowship hall is reserved for 2:00-6:30 PM"
```

Or on negative response:

```yaml
preflight:
  location_confirmed:
    status: rejected
    ...
    note: "Need to pick a different date — fellowship hall booked for wedding"
```

Rejected status should surface clearly on the next `event-status` call and
the user should be prompted to decide (reschedule / cancel / find alternate
location).

### Step 5 — show updated preflight

Display the full preflight checklist with this item now ✓ and anything
still outstanding.

## Guardrails

- NEVER send without explicit user approval on the draft.
- NEVER auto-confirm — the user must paste in the actual reply (or say "they said yes") before stamping.
- Always log the channel + verbatim (or paraphrase) for audit trail.
- If the POC's preferred_channel is in_person or phone_call, DO NOT attempt
  to auto-send. Surface a reminder and wait.
