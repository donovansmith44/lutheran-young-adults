---
name: Always git pull before git push
description: This repo has an active human collaborator — pull before every push, not just when you hit a rejected-push error
type: feedback
originSessionId: afb7e019-e38a-4ffb-8233-0bd2f7351f23
---
Before any `git push` on this repo, run `git fetch origin && git pull --ff-only origin main` (or equivalent) first. Don't assume the local branch is current just because Sally pushed recently — the user edits files directly on the remote / in their own session and pushes while Sally is working.

**Why:** The user flagged this twice: "pull the code SALLY, you forgot to pull before pushign AGAIN." Sally had caused a rebase conflict earlier because the remote had diverged. It wastes the user's time to untangle that when a pre-push pull would have prevented it.

**How to apply:**
- Make `git pull` part of the standard commit-and-push flow, even if the last push was two minutes ago.
- If `pull` pulls new commits: stop, reread the diff, and decide whether Sally's in-flight work still makes sense on top of the new state before pushing on.
- If the remote has been heavily restructured (different template layout, new fields, etc.), don't just force-replay Sally's change — re-evaluate whether the change is still the right thing.
- Fast-forward only (`pull --ff-only`) is safest; a merge commit adds noise to this repo's scratchpad-style history.
