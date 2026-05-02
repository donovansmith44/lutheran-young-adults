# LYA Event Planner — progress log

Running checklist so any session (human or Claude) can pick up from the current state without reading every commit.

## How this works

- **Done** — shipped, don't redo unless broken.
- **In progress / parked** — partially implemented or currently iterating.
- **Next up** — the most likely next task.
- **Ideas / someday** — floated in chat, not committed to.

Keep the top section trimmed. When something gets done, move the summary into "Done" (single bullet) and clear its detail.

---

## Done

### Brochure (physical tri-fold, roll-fold)
- Content pipeline: `lya_event_series.md` → `build.py` → `templates/brochure_template.html` + Tailwind → WeasyPrint PDF.
- Tri-fold geometry: outside `[ TUCK 3.5in | BACK 4in | FRONT 3.5in ]`, inside mirrored `[ SCHEDULE 3.5 | PHOTO 4 | ABOUT 3.5 ]` — tuck narrow, middle widest, outer panels match. Dashed dividers at 31.82% / 68.18%.
- Outside face:
  - TUCK panel = "Connection" mission letter (salutation + mission text + scripture + citation `(Hbr. 10:24-25, ESV)`).
  - BACK panel = contact page — logo, CONTACT eyebrow, QR ("Scan to RSVP"), phone `(614) 556-0607`, email `donovan.smith44@gmail.com`, tagline.
  - FRONT panel = cover — "Lutheran Young Adults" / subtitle "Connecting Confessional Lutherans". Title renders on two lines ("LUTHERAN" / "YOUNG ADULTS") via `build.py` splitting on the first word and joining the rest with `&nbsp;`; cover font-size is 19pt to fit the narrower 3.5" front panel.
- Inside face (table layout so each event row aligns across columns):
  - Left (schedule): date + event name + italic-Cormorant location caption above name + times list. "Event Schedule" heading, bottom-left footnote "* Event details subject to change as the Lord wills".
  - Middle (photo): single photo slot spanning all rows via `rowspan`.
  - Right (about): italic Cormorant entries per event (title, optional headline, optional serif-body blurb). "What to Expect" heading.
- Events currently with descriptions: Personality Day (headline + blurb), America's 250th (headline + blurb), The Odyssey (blurb only).
- RSVP flow: `build.py` regenerates `assets/qr-rsvp.svg` each build from `RSVP_URL` (default mailto to donovan.smith44@gmail.com with prefilled subject + body template).

### Repo / infra
- Remote: `donovansmith44/lya-event-planner` (user's fork).

## In progress / parked

*(none currently)*

## Next up

- Drop a real photo at `assets/photo.jpg`; the inner-middle panel will pick it up automatically.
- Fill in headlines/blurbs for the later events (Sept — Community Service Day, Oct — Fall Cookout, Nov/Dec TBD) when the copy is ready.

## Ideas / someday

- Make the `--max N` default configurable per format (flyer currently shares the default with brochure).
- Offer a one-command build that regenerates flyer + brochure together.
- RSVP destination upgrade: swap the mailto in `build.py` for a Google Form / Partiful / Eventbrite link once one exists (single-line edit; QR regenerates).

## Gotchas for future sessions

- Brochure is designed for `--max 3` (default). `--all` has always overflowed past 2 pages and is not the target.
- Never hand-edit `brochure.html` / `brochure.css` — they're regenerated from `templates/brochure_template.html` + `src/brochure.css` on every `build.py` run.
- Print in grayscale from the printer driver if needed — don't strip color from the source.
