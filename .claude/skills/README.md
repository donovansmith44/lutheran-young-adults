# LYA orchestrator skills

Skills live in this directory as subfolders, each with a `SKILL.md` that
describes what the skill does and how Claude should execute it when the
user invokes it conversationally or via `/<skill-name>`.

## Current skills

### Event lifecycle (in typical order of use)

| Skill | What it does |
|---|---|
| `event-create` | Draft new event markdown, set up preflight, create Trello + Sheet + brochure preview |
| `event-confirm` | Confirm one preflight item (location, date, budget) with the relevant POC |
| `event-invite` | Draft + send personalized invites; blocked until preflight is complete |
| `event-set-status` | Manually log an RSVP reply (coming / maybe / not_coming) |
| `event-status` | Dashboard: preflight state, RSVP counts, help-wanted status |
| `event-watch` | Risk-report health check — cross-checks Trello, Sheet, RSVPs, preflight, deadlines. One-shot or loop with desktop notifications. |
| `event-help-wanted` | Draft + send help-wanted messages to confirmed attendees with the Sheet link |
| `event-remind` | Draft + send reminders to pending invitees |
| `event-change` | Notify accepted+maybe about a time/venue change |
| `event-cancel` | Notify accepted+maybe about a cancellation |
| `event-archive` | Move per-event encrypted caches to cold storage post-event |

### People / invite-list management

| Skill | What it does |
|---|---|
| `people-add` | Add a new contact to `people.yaml` interactively |
| `people-edit` | Modify an existing entry (style samples, preferred_channel, etc.) |
| `people-skip` | Skip a person for a specific event without removing them |
| `people-list` | Show the current roster |
| `people-remove` | Delete an entry + rekey (with confirmation) |

### Marketing

| Skill | What it does |
|---|---|
| `marketing-build` | Render an existing template (flyer, brochure, …) |
| `marketing-new-template` | Scaffold a NEW template (poster, Save the Date, social post, etc.) with our design system |

## How skills compose

Claude Code reads these `SKILL.md` files automatically; user requests get
routed to the matching skill. Skills can invoke each other (e.g.
`event-create` ends by pointing at `event-confirm`, never by skipping
ahead to `event-invite`).

The boundary between skills is usage-driven, not technical. Any skill
can call any `orchestrate.py` primitive — the skills are just the
conversational layer.

## Adding a new skill

1. `mkdir -p .claude/skills/<name>`
2. Write `SKILL.md` with YAML frontmatter (`name`, `description`) and
   instructions. Model after the existing skills.
3. If the skill needs new Python capability, add it to `orchestrate.py`
   as a subcommand rather than hiding it inside the SKILL.md — keeps the
   code auditable.
4. Commit. On next Claude Code session the skill is live.
