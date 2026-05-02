---
name: Tri-fold brochure — shipped
description: Brochure template is live. Invoked via build.py --format brochure.
type: project
originSessionId: afb7e019-e38a-4ffb-8233-0bd2f7351f23
---
The tri-fold brochure is **done and in the repo** (superseding the earlier
"planned" status of this memory).

**Where it lives:**
- Template: `templates/brochure_template.html`
- CSS source: `src/brochure.css`
- Built CSS: `brochure.css` (compiled via Tailwind standalone)
- Output: `brochure.pdf` (letter landscape, 2 pages = outside + inside face)
- Build command: `python3 build.py --format brochure`

**Layout (final, approved):**

Outside face (printed L-to-R, folded C-fold):
- Left panel: scripture + mission (tucks inside when folded)
- Middle panel: back cover — contact info + QR code (teal background)
- Right panel: front cover — title + logo + subtitle (visible when closed)

Inside face:
- Left column: event schedule (per-event table)
- Middle column: "What to Expect" narrative per event
- Right column: single photo (rowspan all), aligned to first event row

Uses the same palette/type system as the flyer: pink `#fad5cd` background,
teal `#01404f` text, Montserrat display + Cormorant Garamond italic
accents, church logo from `assets/logo.png`.

**How the orchestrator uses it:**
- `event-create` skill calls `build.py --format brochure` as part of the
  new-event setup
- `marketing-new-template` skill references this template's CSS tokens
  when scaffolding new marketing pieces (Save the Date cards, posters,
  social posts, etc.)

**Card-paper / CRISP printing advice** (user requested this knowledge):
- 80–100 lb cover stock
- Score before folding (bone folder or scoring board)
- Fold with the grain
- Burnish the crease with a bone folder post-fold
- For laser prints, avoid solid dark panels at fold lines (toner cracks).
  This design has a solid teal back panel; suggested mitigation: pink
  gutter strip at each fold edge, or print on inkjet.
