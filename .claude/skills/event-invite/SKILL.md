---
name: event-invite
description: Draft personalized invite messages per invitee (in Donovan's voice + each person's style), review in-chat, send via sms-gate.app / email / offline-reminder. Blocked until preflight is complete. Respects per-event skip_list and per-person preferred_channel.
---

# event-invite

## When to invoke

User says "send invites for June" / "draft the invite texts" / "let's invite everyone."

## Arguments

- `<slug>`: event slug. Required.

## PREFLIGHT CHECK (first thing, do not skip)

Read the event's encrypted state. If any preflight items are not `confirmed`,
BLOCK and show:

```
cannot draft invites — preflight incomplete for 2026-06-personality-day:
  ✓ date_confirmed
  ✗ location_confirmed  ← run /event-confirm location first
  
Run /event-confirm for each missing item, or pass --override-preflight
to proceed anyway (logged in event state).
```

Do not proceed unless all items confirmed OR user explicitly passes
`--override-preflight` (and log that override to the event state).

## Flow

### Step 1 — compute the actual invite list

Start with `events/<slug>.md` invite_list (or everyone with `default_invite: true`
if empty). Then:

- Read `skip_list` from event frontmatter — remove those people
- Remove anyone with no way to contact (no phone + no email + no relay_via + no in_person reminder target)

Show the final list to the user; they can still prune.

### Step 2 — classify by channel

For each invitee:

- `preferred_channel: sms` → "will text"
- `preferred_channel: email` → "will email"
- `preferred_channel: phone_call` → "will surface reminder for you to call"
- `preferred_channel: in_person` → "will surface reminder (and draft relay message if relay_via is set)"

Show the plan:

```
INVITE PLAN — 2026-06-personality-day (10 people)

SMS (7):           Jane, Donny, Sam, ...
Email (2):         Pastor Zion, Pastor Mark
Reminder to call (1): Aunt Ruth (you'll call her)
Relay (1):         Foo → via Pastor Mark at St. Mark's
```

User approves the plan before any drafting.

### Step 3 — draft per person

For each recipient in the approved list, draft the message:

- **SMS / email:** Read `voice.md` (Donovan's global voice) + that person's
  `style_samples`, `relationship`, `context` from `people.yaml`. Write the
  message in-chat. Include: event name, date, time, location, a direct ask.
  Match length and tone to prior style_samples.

- **In-person reminder** (for in_person-only contacts): write a TODO-style
  note for Donovan: "Invite Foo in person next time you see him — event is
  June 6, 2pm at Zion, Personality Day. He doesn't text."

- **Relay draft**: if the in-person person has `relay_via`, draft a message
  to the relay asking them to pass the invite along. Same review gate.

Show each draft one at a time OR in a batch with per-item approve/edit.
User can edit inline, regenerate, or skip an individual.

### Step 4 — send on approval

For each approved draft:

- SMS → `orchestrate.py sms-send --to <phone> --body <text>`
- Email → `orchestrate.py email-send --to <addr> --subject ... --body ...`
- In-person reminder → append to `~/.config/event_planner/reminders-<slug>.age`
- Relay → send to the relay via their preferred_channel

Log outbound in the event state with timestamp + channel + approved text.

### Step 5 — report

Show summary: N sent, N reminders logged, N skipped. Next step: wait for
RSVPs, log them with `/event-set-status` as they come in.

## Guardrails

- Preflight gate is hard. Only `--override-preflight` bypasses, and it's
  logged.
- Every draft requires explicit user approval before send.
- Respect `skip_list` absolutely — never draft for skipped people.
- Respect `preferred_channel: in_person` and `phone_call` — never try
  to auto-send to those.
- If a person has both `skip_list` entry AND is in default invite list,
  the skip wins.
- Never send the same invite twice. Check event state for already-sent
  logs before drafting.
