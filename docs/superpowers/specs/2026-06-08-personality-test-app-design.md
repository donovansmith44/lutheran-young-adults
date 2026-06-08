# Personality Test + Session Admin — Design Spec

**Date:** 2026-06-08
**Status:** Approved for planning
**Context:** Sub-project of the Lutheran Young Adults (LYA) website. This is the dynamic personality-test application used at the **Personality Day** event (2026-06-20 at Zion, 766 S High St, Columbus, OH). The marketing website (landing, About, Contact, events hierarchy) is a separate, later sub-project; the test will be reachable at a clean URL now and linked from the Personality Day event page later.

---

## 1. Goals

- Let attendees take a short MBTI-style personality test on their phones, get their 4-letter type, and (optionally) share it with others at the same event.
- Automatically sort attendees into two activity groups (**scavenger hunt** / **games**) based on their personality, revealed on a timer.
- Give the organizer (admin) a durable, cross-device page to manage test "sessions".
- Match the LYA brochure's look: teal `#01404f`, pink `#fad5cd`, pink-deep `#f5bbb0`, cream `#fff8f2`; **Montserrat** for UI, **Cormorant Garamond** italic for grace notes. Modern, soft, rounded — explicitly not sharp gray panels.
- **Doctrinal soundness:** keep "Christ for you" in view. No question should lead a taker to reflect in a manner displeasing to God as confessed in the three ecumenical creeds (Apostles', Nicene, Athanasian) and the Lutheran Confessions (Book of Concord). Items that do are reworded (preferred) or excluded — see §7.

## 2. Non-goals (this spec)

- The marketing website and events hierarchy (separate spec).
- Accounts/passwords for test-takers (username-only by explicit choice).
- Native push notifications.
- Validity/accuracy claims about the test beyond what OEJTS provides.

## 3. Stack & hosting

- **Firebase Hosting** serves a single-page web app (test-taker UI + admin UI).
- **Cloud Firestore** stores all data; real-time listeners drive live updates (timer countdown, shared list, admin roster, reveals).
- **Firebase Auth**: Google sign-in for admins; **anonymous auth** for test-takers (every device becomes an authenticated client without anyone creating an account).
- **No server code / no Cloud Functions** — all logic runs client-side, guarded by Firestore security rules. Keeps the project on Firebase's free (Spark) tier and fast to ship.
- Custom domain `lcmsyoungadults.org` (test under a clean path, e.g. `/personality-test`).

**Trust model:** Test-takers are username-only by design, so a `takers` document is editable by any signed-in app client. Anonymous auth blocks random internet bots but not deliberate impersonation by another attendee — an accepted trade-off for a friendly church event. `sessions` and `admins` are writable only by allowlisted admins, enforced in security rules.

## 4. Routes

| Route | Purpose |
|---|---|
| `/personality-test` | Username entry → test → result (the test-taker experience) |
| `/personality-test/results` | Returning view of one's own result + the session's shared list (may be folded into the post-submit screen) |
| `/admin` | Session management; gated by Google sign-in + admin allowlist |

## 5. Data model (Firestore)

### `takers` — one document per username
Document id = normalized username (trimmed, lowercased).
- `username` — display form as entered
- `answers` — map/array of the 32 OEJTS responses (1–5), saved as the user goes
- `completed` — bool
- `type` — 4-letter type once completed (e.g. `INTJ`)
- `axisScores` — the four OEJTS axis sums (8–40 each)
- `seRank` — integer 1–8 (see §8 table); set on completion
- `seStrength` — number used only as a tiebreak (see §8)
- `sharing` — bool (opted in to share / see others)
- `sessionId` — id of the session active at submit time, or `null` (session-less)
- `group` — `"scavenger"` | `"games"` | `null`
- `groupOverride` — bool; if true, admin set the group manually and recomputes must not move them
- `createdAt`, `updatedAt`, `completedAt`

### `sessions` — one document per session
- `name` — admin-given label
- `status` — `"active"` | `"ended"` | `"archived"`
- `timerMinutes` — N (default 30), set at start, editable before reveal
- `startedAt`, `endedAt`
- `groupsFrozenAt` — timestamp the split was computed/locked (null until reveal)
- `createdBy` — admin email

**Assumption:** at most one `active` session at a time. Starting a session is blocked while another is active.

### `admins` — the allowlist
- A small collection (or single doc) of allowed admin emails. The primary admin (`donovan@lcmsyoungadults.org`) can add/remove entries to hand off and later revoke admin access.

## 6. Test-taker experience

1. **Username entry** (`/personality-test`): minimal screen — title "Personality Test", a username field, a "Begin" button. On submit, normalize and look up:
   - **New** → create the `takers` doc, start at question 1.
   - **Existing** → load it and resume at the first unanswered question, or go straight to results if `completed`. This is the cross-device + interrupted-test recovery path, all keyed on the username.
2. **The test**: 32 OEJTS items, each a 5-point choice between two opposing statements, rendered as tappable points between two Cormorant-italic poles (e.g. "not me" ↔ "very me"). A prominent **progress bar with "Question X of 32"** sits at the top. **Each answer autosaves to Firestore immediately**, so a dropped connection or closed tab never loses progress.
3. **Submit → sharing prompt**: compute `type`, then a single yes/no — *"Share your result with others in this session who have also taken the test and shared theirs?"*
4. **Result screen** (pink background, teal type) shows exactly:
   > **{username}, your answers to the test questions indicate that you are an {TYPE}!**
   > {if T > 0: *Check back in {T} minutes to find out what activity group you'll participate in* | if T = 0: *You're in the scavenger hunt group!* **or** *You're in the games group!*}
   >
   > To read more, click here: `https://www.16personalities.com/{type}-personality` (lowercase type)

   The "check back in {T} minutes" line live-updates and flips to the group reveal when T hits 0 — no manual refresh. (All 16 types start with a vowel sound, so "an {TYPE}" is always grammatical.)
5. **Shared list**: if sharing, show the session's shared results below — each row `User: {username}  Test Result: {TYPE}`, where `{TYPE}` is a **clean teal link with no underline** to that type's 16personalities page. A toggle lets the user **opt in/out anytime**: opting out immediately hides the list (you only see others while you share); opting back in restores it.

## 7. OEJTS questions & scoring

- Source: **Open Extended Jungian Type Scales (OEJTS)** — public domain, 32 items, ~5–10 min, scores the four axes (I/E, S/N, F/T, J/P).
- Each item maps to one axis with a direction; scoring sums each axis (8–40, midpoint 24) and picks the letter by which side of the midpoint the sum falls. The exact item list and per-item scoring key (from the OEJTS source) will be transcribed into a scoring table during implementation.
- The four letters concatenate to `type`.

### Doctrinal review of the item pool

Per the §1 principle, the 32 OEJTS items are reviewed against the three ecumenical creeds and the Lutheran Confessions, keeping "Christ for you" in view.

**Process — flag and confirm:** Claude flags candidate items with a written rationale; **the user (and/or their pastor/vicar) approves the final treatment before implementation.** No item is changed or removed without that confirmation.

**Default handling — reword, not delete:** a flagged item is **reworded** to strip the objectionable framing while preserving the trait it measures, so each axis keeps its 8 items and OEJTS scoring stays intact (midpoint 24). An item is only *excluded* if it can't be salvaged by rewording; in that case the affected axis is rescaled to its remaining item count (midpoint = 3 × items on that axis).

**Currently flagged candidates (pending confirmation):**

| # | Original poles | Concern | Proposed reword |
|---|---|---|---|
| 3 | "skeptical" ↔ "wants to believe" | Frames *believing* as a temperament/wish; faith is the Spirit's gift, not self-summoned (Small Catechism, Third Article). The clearest flag. | "questions new claims until they're proven" ↔ "readily embraces new ideas" |
| 27 | "bases morality on justice" ↔ "bases morality on compassion" | Locates the *basis* of morality in a personal inclination rather than God's revealed Word. For consideration. | "weighs choices by fairness and logic" ↔ "weighs choices by empathy and others' feelings" |
| 23 | "follows the heart" ↔ "follows the head" | "The heart is deceitful" (Jer. 17:9); "follow your heart" trope. Borderline — really about decision style. | "decides with feelings" ↔ "decides with logic" |

The remaining 29 items are judged doctrinally neutral. Final wording is subject to the user's confirmation.

## 8. Group assignment

### Se ranking (confirmed)
Each type maps to an extraverted-sensing (Se) rank by Se's position in the 8-function (Beebe) stack. Rank 1 = highest Se.

| Se rank | Stack position | Types |
|---|---|---|
| 1 | Dominant | ESTP, ESFP |
| 2 | Auxiliary | ISTP, ISFP |
| 3 | Tertiary | ENFJ, ENTJ |
| 4 | Inferior | INFJ, INTJ |
| 5 | Opposing (shadow) | ISTJ, ISFJ |
| 6 | Senex (shadow) | ESTJ, ESFJ |
| 7 | Trickster (shadow) | INFP, INTP |
| 8 | Demon (shadow) | ENFP, ENTP |

`seStrength` (tiebreak only): derived from how strongly the taker leans Extraverted and Sensing (distance of the I/E and S/N sums from the midpoint). More extraverted + more sensing = stronger Se. Used to order takers who share the same `seRank` at the split boundary.

### The freeze (reveal moment)
Triggered when the session **first reaches T = 0**, OR when the admin **ends the session** or presses **"reveal now"** — whichever comes first. Run once, in a Firestore transaction, over a snapshot of **every active taker in the session** (completed and still-testing):

1. **Completed takers** form the trait-based split: sort by `(seRank` asc, `seStrength` desc`)`; assign the **top half to scavenger hunt**, the rest to **games**. Odd count → **scavenger hunt takes the extra one** (`ceil(n/2)`).
2. **Still-testing takers** are assigned to whichever group is currently **smaller**, to keep numbers even (tie → scavenger).
3. Stamp `sessions.groupsFrozenAt`.

After the freeze, **finishing the test has no bearing on a taker's group** — the assignment is locked (they still receive their type, link, and shared list on submit).

### After the freeze
- Any taker who becomes **active in the still-`active` session after the freeze** (new joiner, or someone who hadn't started) and has no group is assigned to the currently **smaller** group (tie → scavenger), immediately, so the banner can show it.
- Whichever client first observes T ≤ 0 runs the freeze transaction (the admin page, open at the event, is the natural one; a taker's device is the fallback).

### Reveal timer
- `T = max(0, timerMinutes − minutes since startedAt)`, computed client-side and updated live.
- While T > 0 the taker sees "check back in {T} minutes"; at T = 0 they see their group.

### Notification while still testing (Option A)
If the freeze happens while a taker is mid-test, a **persistent teal banner** pins to the top of the test screen for the rest of the test: *"Time's up — you're in the {Scavenger Hunt / Games} group. Finish your test for your full result."* It never blocks them; the group also appears on the result screen. (No modal.)

### Admin override
From the admin page, the admin can move any individual between groups at any time; this sets `groupOverride = true` so recomputes/rebalances never move that person. Admin also has **"reveal now"** (force T = 0 early) and a **recompute/rebalance** action.

## 9. Admin & session management (`/admin`)

- **Access**: Google sign-in; entry granted only if the signed-in email is in `admins`. The admin can add/remove admin emails (hand-off + revoke). Works on any device; nothing to leak.
- **Start session**: creates an `active` session with chosen N (timer minutes). Blocked if another is active.
- **Live roster**: as people submit, a live table shows username, type, Se rank, current group, sharing on/off.
- **End session**: stamps `endedAt`, status → `ended`; triggers the freeze if not already done. From then on, **new submissions are session-less** (`sessionId = null`) and are not added to it.
- **Edit**: rename a session; adjust N before reveal.
- **Reveal now / recompute**: force the reveal early; rebalance after a batch of latecomers (respecting `groupOverride`).
- **Archive**: hide ended sessions from the main list without deleting; kept indefinitely.
- **Delete**: guarded by a modal that requires typing **`DELETE`** exactly before anything is removed.
- **Persistence**: all state in Firestore — the admin page survives lost connections, refreshes, and device switches.

## 10. Look & feel

- Brochure palette and fonts (Montserrat UI, Cormorant Garamond italic accents).
- Rounded cards, soft shadows, generous spacing, pill buttons.
- Landing: title + username field + Begin button only.
- Question: top progress bar ("Question X of 32"), the OEJTS choice as tappable points between two italic poles.
- Result: **pink→cream background, teal type**, group as a teal pill, underline-free teal "Read more" and type links.

## 11. Open items / assumptions

- One `active` session at a time (flag if concurrent sessions are ever needed).
- Exact OEJTS item text + per-item scoring direction to be transcribed from the source during implementation.
- Final doctrinal treatment of the flagged items (§7) awaits the user's / pastor's confirmation before implementation.
- Username collisions: entering an existing username *is* that user (resume), consistent with username-only re-entry; distinct usernames are encouraged.

## 12. Later: marketing-site integration

When the marketing site is built, the Personality Day event page (`/events/2026/june/personality-day`) links to `/personality-test` as a resource. The design system established here is shared with that site.
