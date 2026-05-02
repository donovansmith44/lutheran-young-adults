---
name: User identity — Donovan Smith
description: Who the primary user of this project is and what that implies for personalization, voice, and tooling setup
type: user
originSessionId: afb7e019-e38a-4ffb-8233-0bd2f7351f23
---
**Donovan Smith** is the primary user of the event_planner project. He is
simultaneously the organizer and the SMS texter for the Lutheran Young
Adults (LYA) group in central Ohio — a 20s/30s confessional Lutheran
fellowship across several parishes (Zion, St. John's Dublin, St. Mark's,
etc.).

**Implications for the tooling:**

- `voice.md` describes Donovan's writing voice — Claude drafts outbound
  messages in that voice.
- `people.yaml` `style_samples` are "how Donovan talks to this person"
  (casual with close friends, formal with pastors, etc.).
- sms-gate.app is installed on **Donovan's Android phone** (model may
  change — phone-agnostic via `.env`). Replies arrive on his phone and
  he logs them via `/event-set-status`.
- Donovan's age public key is what should be in `recipients.txt` for
  encrypted config access. The current scaffolding key
  (`age1aewj3d6xdyffe3vksj37m5q6f8wltkajzga4vtft2vmqh92ew9yslqa26j`) is
  a dev-laptop-generated placeholder; Donovan replaces or appends with
  his own.
- Email: `donovan.smith44@gmail.com`.
- Primary repo: `https://github.com/mlaine1/lya-event-planner` (private).
  Note: the repo is under `mlaine1` as an artifact of initial setup;
  Donovan has admin collaborator rights.

**Operating preferences:**

- "Bosses push, leaders pull." Delegates tasks by surfacing the pool,
  not assigning individually, to avoid burnout.
- Minimalism in marketing pieces and texts. Non-corporate phrasing.
  Warm and direct.
- Iterates quickly; values seeing pushed output on GitHub over lengthy
  terminal transcripts.
- Privacy-conscious about contacts; won't "screw people over" on data.
