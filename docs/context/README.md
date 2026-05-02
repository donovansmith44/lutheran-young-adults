# Project context — for Donny

These files are Claude's internal "memory" notes from the original
build sessions. They live here as a backup / reference so that:

1. If Claude's local memory is ever lost, you (or a future Claude
   session) can rebuild context from this folder.
2. You have a single place to read the architectural decisions, the
   "why" behind them, and your own preferences as Claude understood
   them.

## A note on tone

These were written by Claude *for* future Claude. So they refer to
you in the third person ("Donovan said X", "user prefers Y"). It's
not weird intentionally — it's just how Claude writes notes to
itself. Don't be thrown by it.

## What's in here

| File | What it covers |
|---|---|
| `MEMORY.md` | Index of all the memory files (what Claude loads first each session) |
| `user_donovan_smith.md` | Who you are, what implications that has for tooling (your voice, your phone, your age key) |
| `project_event_orchestrator_architecture.md` | **Read this first.** End-to-end architecture: chat→skills→primitives, encrypted config, Sheet↔Trello sync, preflight gate, what's built, what's pending |
| `project_event_planner_workflow.md` | Earlier framing (markdown→marketing pipeline). Mostly superseded by the orchestrator doc above, but still valid as backstory |
| `project_trifold_brochure_plan.md` | Brochure status (shipped) + CRISP card-stock printing tips you asked for |
| `project_canva_integration_options.md` | Canva paths we considered and why we didn't pursue them |
| `feedback_flyer_design_approved.md` | The design baseline: pink #fad5cd + teal #01404f + Montserrat + Cormorant + church logo |
| `feedback_preserve_source_wording.md` | Don't paraphrase source content (you got burned on this once) |
| `feedback_push_early_dont_batch.md` | Push WIP immediately so you can review on GitHub |
| `feedback_always_pull_before_push.md` | Always `git pull --ff-only` before pushing — you edit on the remote |
| `feedback_check_existing_auth.md` | Probe for existing creds before asking you to log in |

## Where to start

1. Skim `MEMORY.md` for the full file map.
2. Read `project_event_orchestrator_architecture.md` end-to-end —
   that's the source of truth for how the system works.
3. Read `user_donovan_smith.md` to see what Claude believes about you
   and correct anything that's wrong.
4. Browse the `feedback_*` files to see the rules of conduct Claude
   has internalized.

## How to update these

If something changes (new preference, architectural decision, etc.):

- The **canonical copy** Claude actually reads is at
  `~/.claude/projects/-home-mlaine3-event-planner/memory/` on
  Donovan's laptop. That's what gets loaded each session.
- This `docs/context/` folder is a versioned **backup**. After
  significant changes, ask Claude to "sync the memory backup" and
  it'll re-copy from the live location to here.

The two locations can drift. The repo copy is for posterity / sharing
with collaborators / disaster recovery — it is *not* automatically
read by Claude on a fresh checkout.
