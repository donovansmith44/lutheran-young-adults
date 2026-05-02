---
name: Approved flyer design baseline — keep these choices
description: Design decisions on the 1-page flyer that the user validated ("passable now"); don't revisit them without cause
type: feedback
originSessionId: afb7e019-e38a-4ffb-8233-0bd2f7351f23
---
As of commit `48e1454`, the user approved ("this thing you have so far in the PDF is actually passable now") this design baseline for `flyer.pdf`. Preserve these choices unless the user explicitly asks to change them:

- **Palette:** pink background `#fad5cd`, deep teal `#01404f` for all text and accents. Pulled from the source Excel fill/font colors.
- **Typography:** Montserrat variable (assets/fonts/Montserrat-variable.ttf) as display; Arial as body. 800–900 weights for display, lowercase uppercase contrast via CSS.
- **Church logo:** the line-drawing church icon extracted from the Excel's embedded image (xl/media/image1.png → assets/logo.png).
- **Banner composition:** title "LUTHERAN YOUNG ADULTS" centered at top, "EVENT SCHEDULE" spaced-caps below it; logo + flanking horizontal rules stacked *below* the title (not side-by-side).
- **Event blocks:** large "`06 June`" style date (22pt, "06" weight 800, "June" weight 300, month capitalized via text-transform); bold event title line at weight 900 12.5pt; 1.5pt teal underline; time/activity list in two columns underneath.
- **Right column (aside):** just the Hebrews 10:24-25 verse. NO mission statement on the flyer, NO decorative opening quote mark.
- **Contact box:** bordered 1pt teal rectangle at bottom, 3 rows (Event Organizer / Location / Contact), Montserrat bold labels.
- **Layout:** letter portrait, one page, with roughly 25% empty pink at the bottom (matches the source Excel example).

**Why:** The user iterated through ~9 versions. The final validated design matches the aesthetic of their source Excel ("example_flyer_wrong_sizing.pdf") while fitting 8.5×11 properly. Earlier experiments that failed and should not be retried absent new direction: centered "wedding schedule" dotted-leader style, 2×4 event grid, banner with side-by-side logo+title, scripture with decorative oversized opening quote, mission statement on the flyer.

**How to apply:** When making further edits to `flyer.pdf`, keep the above as the starting point. Small tweaks (dropping events, adjusting spacing) are fine. Full redesigns should only happen if the user explicitly asks.
