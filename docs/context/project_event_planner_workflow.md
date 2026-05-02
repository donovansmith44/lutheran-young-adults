---
name: Event planner two-stage workflow
description: User's intended flow for this project — draft markdown from raw event input, then transform into marketing format
type: project
originSessionId: afb7e019-e38a-4ffb-8233-0bd2f7351f23
---
This project (`/home/mlaine3/event_planner`) is for planning events via a two-stage markdown pipeline:

1. **Stage 1 — Authoring:** Take raw input (e.g. an Excel spreadsheet, rough notes) and produce a structured markdown document describing the event.
2. **Stage 2 — Marketing transform:** Convert that authoring markdown into a "nice format for marketing purposes" — e.g. one-pager handouts, flyers, social posts.

**Why:** The user plans multiple events (the first concrete example is a Lutheran Young Adults monthly series organized by Zion Evangelical Lutheran Church, central Ohio, contact (614) 556-0607). Having a repeatable pipeline beats formatting each one from scratch.

**How to apply:** When the user drops in a new event source (spreadsheet, notes, rough description), default to producing a clean authoring-stage markdown first, then ask what marketing output format they want (one-pager handout, flyer, social post, email blast, etc.) rather than guessing. The handout format established in `lya_event_series.md` is a reference example — opening scripture/quote (if provided), mission/intro paragraph, per-event sections with time tables, contact block at the bottom.
