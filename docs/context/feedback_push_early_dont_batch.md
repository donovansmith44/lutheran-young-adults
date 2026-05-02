---
name: Push early, don't batch — this user iterates live against pushed output
description: Commit and push work-in-progress as soon as it renders; user reviews by pulling/viewing the repo, not by reading terminal output
type: feedback
originSessionId: afb7e019-e38a-4ffb-8233-0bd2f7351f23
---
On the event_planner project, commit and push immediately as soon as any visual artifact renders (flyer draft, PDF, etc.), even if it's imperfect or wrong. Don't hold work for polish before pushing.

**Why:** The user said directly: "push everything out as soon as you get it so I can see, I don't wanna wait on you to think, you're too slow." They're reviewing visuals by looking at the GitHub repo, not waiting for Sally's internal iteration to finish. Waiting until something is "good" feels slow to them; it's faster to push broken/ugly and iterate than to get it right before the first push.

**How to apply:** Whenever a rendered output exists (PDF generated, image saved, first-pass HTML rendered), immediately `git add -A && git commit -m "wip: brief note" && git push` before continuing to refine. Use short throwaway commit messages — this repo's `main` branch is effectively a scratchpad, and the user values rapid visibility over commit-history cleanliness. Only after the user confirms the artifact is good should Sally bother squashing/cleaning commits.
