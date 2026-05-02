---
name: Canva integration — explored, not pursued
description: User asked about markdown → Canva templates. Three paths exist; none chosen. HTML→PDF pipeline was kept instead.
type: project
originSessionId: afb7e019-e38a-4ffb-8233-0bd2f7351f23
---
User asked early on whether the markdown could drive a Canva template.
Three paths were identified (Canva Connect API + Brand Template; Canva
CSV Bulk Create; manual PDF import), each with tradeoffs documented
in the earlier eval.

**Decision: not pursued.** The HTML → PDF pipeline with reusable templates
(`templates/flyer_template.html`, `templates/brochure_template.html`)
turned out to serve the need well. Variable event schedules (different
row counts per event) would have been awkward to bind to a fixed Canva
Brand Template, and the API setup overhead didn't pay off for a
single-organizer use case.

**Revisit only if:**
- User explicitly asks to collaborate on designs in Canva's UI
- The LYA brand expands beyond Donovan designing everything himself
- A design-oriented collaborator joins and wants Canva as their editor

Until then: new marketing pieces are scaffolded via the
`marketing-new-template` skill using the existing HTML + CSS + Tailwind
system. `templates/flyer_template.html` and `templates/brochure_template.html`
are the reference examples.
