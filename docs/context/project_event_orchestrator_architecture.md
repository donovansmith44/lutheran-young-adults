---
name: Event orchestrator architecture (current)
description: End-to-end architecture for the LYA event orchestrator. Skill-driven conversational interface, scaffold in place, integrations pending credentials.
type: project
originSessionId: afb7e019-e38a-4ffb-8233-0bd2f7351f23
---
## What this project is

Event planning orchestrator for **Lutheran Young Adults (LYA)** — a 20s/30s
confessional Lutheran group in central Ohio, organized by **Donovan Smith**
(who is both the organizer AND the SMS texter, single person).
Goals: go from "let's plan an event" in chat → brochure + Trello board +
Google Sheet + personalized invites + RSVP tracking + help-wanted
coordination, without Donovan burning out or "screwing people over" on privacy.

## Who the user is

**Donovan Smith** — the user of this tool. `voice.md` is Donovan's voice.
`people.yaml` `style_samples` are "how Donovan talks to this person."
sms-gate.app is installed on Donovan's Android. Donovan's age public key
goes in `recipients.txt`. (The current scaffolding key
`age1aewj3d6xdyffe3vksj37m5q6f8wltkajzga4vtft2vmqh92ew9yslqa26j` was
generated on the dev laptop; it stays as dev/backup; Donovan adds his own
before real use.)

## Interface model

**Donovan talks to Claude Code in chat. Claude invokes skills.** Skills live
at `.claude/skills/<name>/SKILL.md`. Each skill reads encrypted config,
drafts content IN THE CLAUDE CODE CONVERSATION (not via Anthropic API),
shows Donovan the drafts, and calls `orchestrate.py` primitives after
explicit approval.

There is NO Anthropic API dependency. Personalization happens because
Claude (this conversation) reads `voice.md` + recipient-specific
`style_samples` and drafts in-chat. Donovan doesn't memorize commands —
he states intent conversationally.

## Scaffolding that exists in the repo today

- **`.claude/skills/`** — 6 skill folders:
  - `event-create` — draft markdown, set up preflight, create artifacts
  - `event-confirm` — confirm one preflight item with a POC
  - `event-invite` — drafts + sends invites (blocked until preflight done)
  - `event-watch` — cross-cutting risk-report health check
  - `people-skip` — per-event skip list
  - `marketing-new-template` — scaffold new marketing pieces
- **`.claude/skills/README.md`** — index + future-skill list
- **`src/secure_config.py`** — decrypt/encrypt helpers (reads `key.txt`
  and `recipients.txt`, writes `.age` files via `pyrage`)
- **`src/event_parser.py`** — parse `events/<slug>.md` frontmatter + body
- **`secret.py`** — CLI for init / edit / cat / rekey / list / pubkey
- **`recipients.txt`** — age public keys that can decrypt project secrets
- **`examples/*.example`** — reference versions of `.env`, `people.yaml`,
  `voice.md` (Donovan-flavored)
- **`templates/trello_recurring_tasks.yaml`** — backbone tasks for every
  event (secure_location, create_brochure, advertise_*, food_signup_list,
  etc.) with `depends_on`, `lead_time_days`, `pullable`, `poc` fields
- **`templates/butler_rules.yaml`** — Trello Butler automation rules
  (deadline slips, at-risk moves, stale-unclaimed warnings) applied
  per board at creation time
- **`templates/flyer_template.html` + `brochure_template.html`** — marketing
  piece templates driven by `build.py` (already shipping)
- **`build.py`** — markdown → PDF (flyer, brochure); reused by orchestrator

## Integrations pending credentials

Four secrets need to land in `~/.config/event_planner/.env.age`:

1. **`TRELLO_KEY` + `TRELLO_TOKEN`** — https://trello.com/power-ups/admin
2. **`GOOGLE_SERVICE_ACCOUNT_JSON`** — Google Cloud service account with
   Sheets + Drive APIs enabled (free project)
3. **`SMS_GATEWAY_URL` + `SMS_GATEWAY_USER/PASS`** — sms-gate.app running
   on Donovan's Android phone (either LAN IP or cloud relay URL)
4. **Donovan's age public key** added to `recipients.txt` (then rekey)

Optional:
- **`SMTP_EMAIL` + `SMTP_APP_PASSWORD`** — Gmail app password for the
  email channel (pastors + anyone with `preferred_channel: email`)

## Storage & state

- **Durable per-event state:** `~/.config/event_planner/event-<slug>.age`
  — encrypted; holds preflight evidence, outbound log, RSVP log,
  task-ID ↔ sheet-row ↔ Trello-card-ID mapping.
- **Rsvp log:** either inside `event-<slug>.age` or separate
  `rsvp-<slug>.age` — manually populated via `/event-set-status`.
- **Contacts:** `~/.config/event_planner/people.yaml.age` — roster
  with style samples, preferred_channel, consent_date, skip-history.
- **Voice:** `~/.config/event_planner/voice.md.age` — Donovan's global
  writing style.
- **Reminders for offline people:** appended to event state or a
  separate `reminders-<slug>.age`.

## Event markdown schema (`events/<slug>.md`)

```yaml
---
slug: 2026-06-personality-day
date: 2026-06-06
start_time: 14:00
location: Zion
host_contact: pastor_zion       # people.yaml key
min_attendees: 6
invite_list: []                  # empty → use everyone default_invite: true
skip_list: []                    # per-event opt-outs (people-skip adds here)
photo_path: assets/photos/...
preflight:
  - location_confirmed
  - date_confirmed
poll_until: 2026-06-06T18:00     # optional; defaults to event date midnight
---

# Personality Day

## Headline
<one-liner>

## About
<paragraph>

## Schedule
| 2:00 PM - 2:15 PM | Introduction |
| ... | ... |
```

## Key design decisions (final, after iteration)

| Decision | Rationale |
|---|---|
| Trello (not JIRA) | Recipients don't need accounts to view (public-url share) |
| Google Sheet for signups (not Trello-direct, not RSVP links) | Zero account friction for 20s/30s helpers; un-claim by deleting name |
| Bidirectional Sheet ↔ Trello sync | Trello = Donovan's tracking tool, Sheet = helpers' UI |
| Sheet sync posts a Trello comment on every claim/unclaim | Triggers Donovan's normal Trello watcher notifications |
| Butler rules on every board | Deadline-passed → move + alert, free via Trello's native automation |
| Manual RSVP logging (no SMS polling) | Privacy — orchestrator never reads Donovan's personal SMS |
| Personalization in-chat, no Anthropic API | Saves cost + complexity; Donovan already talks to Claude |
| Preflight gate before invite | Prevents blasting invites for an unconfirmed venue |
| Every outbound has a review gate | No surprise sends ever |
| `preferred_channel` per person (sms/email/phone_call/in_person) | Respect contact preferences; offline folks get reminders, not auto-sends |
| `relay_via` for offline contacts | Delegate in-person invites via trusted intermediaries |
| Age-encrypted at rest with multi-recipient support | Collaborators can decrypt with their own keys; private keys never shared |

## Rules of conduct (hard constraints)

- **Preserve source wording verbatim.** When turning Excel/markdown into
  marketing pieces, don't paraphrase or substitute characters (emoji, etc.).
  See `feedback_preserve_source_wording.md`.
- **Push early, pull before push.** Commit WIP and push. Always `git pull --ff-only`
  first; Donovan edits files on the remote while Claude works.
- **Never auto-send anything.** Every invite/reminder/cancel/change draft
  is reviewed by Donovan before send.
- **Preflight gate is non-negotiable.** No invite drafting until location
  and date are confirmed (override possible but logged).
- **Data minimization.** Trello / Sheet / brochure see only aggregates and
  names-with-consent, never raw SMS text. Reply text, if logged, stays
  in encrypted local state only.
- **No proprietary lock-in for core comms.** SMS goes through sms-gate.app
  on Donovan's own phone, not a gateway service.

## Current build status (2026-04)

- ✅ Encrypted config machinery (pyrage, multi-recipient, `secret.py` CLI)
- ✅ Event markdown parser
- ✅ Skill scaffolds (6 skills)
- ✅ Recurring tasks + Butler rules templates
- ✅ Example config files
- ⏳ `orchestrate.py` primitives — stubs planned (`trello-create`,
  `sheet-create`, `sheet-sync`, `sms-send`, `email-send`, `trello-board`,
  `sheet-read`, `archive`)
- ⏳ Integrations (Trello, Google Sheets, sms-gate.app, Gmail) — blocked
  on credentials

## Next-step build order once creds arrive

1. Wire `orchestrate.py trello-create` + `trello-board` against Trello API
2. Wire `orchestrate.py sheet-create` + `sheet-sync` against Google Sheets
3. Wire `orchestrate.py sms-send` against sms-gate.app
4. Wire `orchestrate.py email-send` against Gmail SMTP (if used)
5. First real-world test event: likely the June 6 Personality Day
6. Add remaining skills as needed: `event-set-status`, `event-status`,
   `event-help-wanted`, `event-remind`, `event-change`, `event-cancel`,
   `event-archive`, `people-add`, `people-edit`, `people-list`,
   `people-remove`, `marketing-build`

## Ratings at target scale (10-25 person 20s/30s monthly series)

- Attendee experience: 9.5/10 — warm texts, 1 link max, no accounts
- Helper experience: 9.5/10 — 30s to claim, delete-name to un-claim
- Organizer (Donovan) experience: 8.5/10 — main cost is review time;
  setup is ~2-3 hours one-time
- Collaborator onboarding: 9/10 — age-keygen + send pubkey, rekey, done

Scales cleanly to ~40 attendees; starts needing compromises at 40-80;
wrong tool for 100+.
