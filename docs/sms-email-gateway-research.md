# SMS-via-email gateway: feasibility and a better path

**For:** Donny
**Status:** Open question — needs your decision before we change architecture
**Date:** 2026-04-25

---

## What you proposed

> "Send text messages via email and only get responses back to that email
> address so it's safe to check. From the receiver's perspective they get
> it from me (same), but from my perspective I get responses back from
> the email so I can have you read them and update the statuses of the
> Trello yourself without having the security risk."

The intent is clear: **keep your personal SMS inbox private from Claude
(2FA codes, banking, family stuff)**, but route RSVP replies somewhere
Claude *can* safely read so it can auto-update Trello.

## Honest answer: not the way you described, but yes via a slightly
different route

There are three paths. Two work, one doesn't. The one that *doesn't* is
the literal "email-as-SMS gateway" interpretation.

---

## Path A — Carrier email-to-SMS gateways (vtext.com, txt.att.net, etc.)

**What it is:** every US carrier had (has?) an email→SMS bridge. You
email `5551234567@vtext.com` and Verizon turns it into a text. Free.

**Why it doesn't work for what you want:**

1. **Verizon shut down vtext.com in 2023.** The biggest US carrier no
   longer has this gateway at all. AT&T and T-Mobile still do, but you'd
   have to know which carrier each invitee uses, which we don't track and
   shouldn't have to.
2. **Recipients don't see your phone number.** They see a weird
   encoded "from" like `donovan.lya.4f3a@vtext.com` rendered as a
   shortcode. The "feels like a personal text from Donny" experience is
   gone — it looks like a marketing blast.
3. **Replies are unreliable.** Some carriers route the reply back to the
   originating email, some don't. If the recipient just types a new SMS
   instead of hitting "reply," it goes to wherever their phone thinks
   the original came from — which isn't a real number.
4. **It's a deprecated pattern.** Carriers are killing these gateways
   because of spam abuse.

**Verdict:** dead end. Don't build on this.

---

## Path B — Dedicated number from a service (Twilio, MessageBird, etc.)

**What it is:** buy a real US phone number from Twilio (~$1.15/mo).
Outbound SMS is sent from that number. Inbound replies hit a Twilio
webhook → forward to your dedicated email (e.g. `donovan.lya@gmail.com`)
or directly to a script Claude reads.

**Pros:**
- Cleanly separated channels: personal SMS stays on your real cell,
  LYA SMS lives on the Twilio number.
- Claude reads only the LYA inbox. Strong privacy guarantee.
- Reply routing is rock-solid (this is Twilio's whole business).

**Cons:**
- Recipients see a **new number** that isn't your real cell. They save
  it as "LYA" in their contacts. Slightly less warm than "this is a text
  from Donny."
- Small recurring cost: ~$1.15/mo for the number, plus
  ~$0.0079/SMS each direction. A 25-person event with 3 messages each
  ≈ $0.60/event in messaging.
- New account to manage (Twilio).

**Verdict:** works clean, slight UX cost.

---

## Path C — sms-gate.app on your phone + code-side filtering (recommended)

**What it is:** the architecture we already planned, with one addition.
Your phone keeps running sms-gate.app. Outbound texts go from your
real cell — recipients see them as texts from Donny, exactly as today.
**The new piece:** the orchestrator polls sms-gate.app's structured
inbox API and filters incoming messages by sender phone *before*
Claude sees anything.

```
Your phone (sms-gate.app) ─┐
                            │  full incoming SMS stream
                            ▼
              ┌──────────────────────────┐
              │ orchestrator (your laptop) │
              │ filter: is sender in       │
              │ active event's invitee     │
              │ list?                      │
              └────┬───────────────┬───────┘
                   │ yes           │ no
                   ▼               ▼
       Claude sees this      Dropped (never logged,
       (logs to              never seen by Claude)
       event-<slug>.age)
```

**Why this is the right answer:**

1. **Outbound is maximally warm.** Recipients still get an SMS from
   your real cell. Same number as ever.
2. **Privacy is preserved by code, not by channel separation.**
   Claude only ever sees messages from people on the active event's
   invitee list. 2FA codes, banking texts, family — invisible to the
   orchestrator because the sender phone doesn't match the whitelist.
3. **No cloud, no extra accounts, no recurring cost.** Uses what we
   already planned to set up.
4. **Auditable.** The filter is a few lines of Python in `orchestrate.py`.
   You can read it and confirm exactly what Claude sees.

**Caveat:** this depends on you trusting the filter code. The "channel
separation" you originally proposed is a stronger guarantee in the
sense that Claude *physically cannot* reach personal SMS. With Path C,
Claude *could* reach personal SMS if the filter were buggy or removed.

**Mitigation:** the filter is small enough to audit. We can also have
it log "dropped: sender 555-XXXX not in invitee list" (without the
message body) so you can spot-check that personal SMS is being
dropped, not forwarded.

---

## My recommendation

**Path C.** It preserves the "text from Donny" warmth that's central
to the orchestrator's whole design, and the privacy property you want
is achievable with a small auditable filter.

If you want stronger physical isolation (Claude *cannot* reach
personal SMS even if the filter breaks), then Path B is the answer —
but you give up the "from my real cell" warmth and pay ~$1/mo.

Path A is dead. Don't think about it.

---

## What I need from you

Pick one:

1. ☐ **Path C** — proceed as currently planned, plus add the
   sender-phone filter and a "dropped" audit log. No architectural
   change, just an addition to `orchestrate.py`.

2. ☐ **Path B** — buy a Twilio number. I'll write up the setup steps,
   you decide whether the warmth tradeoff is worth it.

3. ☐ **Something else** — push back if I missed an option that
   matters to you.

Reply with the number (or your reasoning if you want to redirect)
and I'll either update `orchestrate.py` (Path C) or write up the
Twilio onboarding (Path B).
