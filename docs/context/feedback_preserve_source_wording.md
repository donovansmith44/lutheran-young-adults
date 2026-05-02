---
name: Preserve source wording verbatim when extracting from authored input
description: When transforming user-authored source material (Excel, docs, notes) into another format, copy the exact words; do not paraphrase, smooth, or restructure prose
type: feedback
originSessionId: afb7e019-e38a-4ffb-8233-0bd2f7351f23
---
When the user gives you authored source material (spreadsheet copy, a document, notes) to transform into another format (markdown handout, flyer, etc.), keep the original wording **verbatim**. Do not:

- Paraphrase prose ("This is why this group has been organized: to serve X" → "This group has been organized to serve X" is a change)
- Drop or swap punctuation you judge stylistic (en-dash vs hyphen, dropped colons)
- Replace emoji with equivalents ("💸" → "$" is a change)
- Rename labels ("Contact" → "Phone" is a change)
- Add explanatory parentheticals ("Pins" → "Pins (bowling)" is a change)
- Add filler lines not in the source ("TBD" section → adding "Details forthcoming.")

You CAN restructure layout — headings, tables, section ordering, rendering an Excel row grid as a markdown table, etc. — because that's formatting, not wording. The rule is: every word, label, punctuation mark, and emoji that appears in the output and derives from source content must match the source exactly.

**Why:** The user ("pgdad1st@gmail.com") caught this on the first event-planner handout and asked me to revert ("no changin the words from the original excel, go back and fix the wording and re push"). This is the Zion Evangelical Lutheran Church / Lutheran Young Adults context — the source prose has specific theological and register choices (e.g. "This is why..." sentence opener, Bible citation format "(Hbr. 10:24-25, ESV)") that shouldn't be smoothed away.

**How to apply:** Before any extract-and-transform task, treat source text as a direct quote — diff your output against the source mentally and justify every divergence as layout, not wording. Additions (new subtitles, marketing copy, etc.) are fine when the user explicitly requests them, separately from the source content.
