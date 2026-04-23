---
name: marketing-new-template
description: Scaffold a new marketing-piece template when the existing flyer/brochure doesn't fit. Conversational — asks what kind of piece, audience, dimensions; pulls the existing design system (pink, teal, Montserrat+Cormorant, church logo) forward by default; scaffolds HTML+CSS+build entry and iterates visually with the user until it looks right.
---

# marketing-new-template

## When to invoke

- "I need a Save the Date card"
- "let's make a poster for the cookout"
- "draft an email blast template"
- "thank-you card for volunteers"
- Anything that isn't one of our existing formats (currently: flyer, brochure)

## Flow

### Step 1 — scope the piece

Ask, conversationally, one at a time:

1. **What is it?** Common types: poster, Save the Date card, social post
   (Instagram square / story / Facebook cover), email invite HTML,
   thank-you card, signup handout, bulletin insert.
2. **Audience and tone?**
   - Congregation-wide (formal) vs. LYA internal (casual)
   - In-person handout vs. digital distribution
3. **Physical dimensions or platform spec?**
   - Print: Letter / A5 / 4×6 postcard / half-sheet / bulletin (5.5×8.5)
   - Digital: Instagram 1080×1080 / story 1080×1920 / email (responsive)
4. **Reuse existing aesthetic or diverge?**
   - Default: reuse (pink `#fad5cd` background, teal `#01404f` text,
     Montserrat display, Cormorant Garamond italic for elegant accents,
     church logo from `assets/logo.png`, diamond-and-rule ornaments)
   - Diverge only on explicit request — the design system is intentional

### Step 2 — generate a plan

Show the user what you're about to build:

```
NEW MARKETING TEMPLATE — Save the Date Card

Dimensions: 4×6 landscape (postcard)
Orientation: horizontal
Sections:
  - Church logo (small, top-left)
  - Date block (large, dominant)
  - Event title (Montserrat bold)
  - Location line
  - Subtle scripture or tagline
  - Footer with contact phone

Files to create:
  - templates/savethedate_template.html
  - src/savethedate.css
  - events/<slug>.md needs no changes
  - build.py gets a new --format savethedate entry
```

User approves or tweaks before any files are written.

### Step 3 — scaffold the files

Create the template HTML + Tailwind-compatible CSS. Reuse existing
tokens from `src/brochure.css` or `src/input.css`:

- `@font-face` declarations for Montserrat variable + Cormorant Italic
- `@theme` block defining `--color-pink`, `--color-pink-deep`, `--color-teal`
- Consistent type scale naming (`--t-eyebrow`, `--t-body`, `--t-display`...)
- Reuse `.diamond` ornament class

Add a new format entry to `build.py`:

```python
FORMATS["savethedate"] = {
    "template": ROOT / "templates" / "savethedate_template.html",
    "html_out": ROOT / "savethedate.html",
    "css_in": ROOT / "src" / "savethedate.css",
    "css_out": ROOT / "savethedate.css",
    "pdf_out": ROOT / "savethedate.pdf",
}
```

### Step 4 — render + review visually

Run `python3 build.py --format <name>`. Render the PDF to PNG via
pymupdf. USE YOUR EYEBALLS — look at the rendered image and compare
to the plan. Check:

- Does it match the approved dimensions? (pymupdf reports page rect)
- Is type sized consistently with our existing pieces?
- Does the palette match?
- Is any text cut off or overflowing?

Show the preview to the user. Iterate until approved — push changes
eagerly so they can see each revision on GitHub.

### Step 5 — document and commit

Update `templates/README.md` (create if absent) with a one-line
description of the new template + its intended use. Commit all files
with a clear message: "Add <type> template for <use case>."

## Guardrails

- ALWAYS pull the existing aesthetic forward by default. Color palette
  and type system are durable assets; the user iterated extensively to
  get them right.
- ALWAYS render and visually inspect the output before declaring done.
  Type checks and dimension prints alone don't tell you if it looks
  retarded.
- NEVER change `src/brochure.css` / `src/input.css` from this skill —
  those are for existing templates. New templates get their own CSS.
- Keep templates small and opinionated. Don't build a generic template
  engine — build a specific piece that works, iterate, move on.
- If the user asks for something radically different aesthetically
  (e.g. "a dark-mode poster"), explicitly confirm the divergence before
  touching the design tokens.

## Worked example: Save the Date card

User: "make a Save the Date card for the July 4 event"

1. Ask: dimensions (they say 4×6 postcard), audience (LYA internal),
   aesthetic (reuse)
2. Plan: horizontal postcard, big date "04 JULY", title, location,
   footer, pull colors + fonts from existing system
3. Scaffold `templates/savethedate_template.html` reusing the brochure
   CSS tokens + a minimal new layout
4. `build.py --format savethedate` renders
5. Inspect render, fix spacing / date typography, re-render
6. Commit once they approve
