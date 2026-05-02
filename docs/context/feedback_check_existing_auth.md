---
name: Check existing auth before asking user to log in
description: Inspect ~/.git-credentials, ~/.config/gh/, env vars, etc. before telling the user to run gh auth login or similar
type: feedback
originSessionId: afb7e019-e38a-4ffb-8233-0bd2f7351f23
---
Before asking the user to authenticate against GitHub (or any service), inspect the machine for existing credentials first:

- `~/.git-credentials` (git credential-store format: `https://USER:TOKEN@host`)
- `~/.config/gh/hosts.yml` (gh CLI config)
- `GITHUB_TOKEN` / `GH_TOKEN` env vars
- `~/.netrc`
- Other tool-specific credential stores (aws, gcloud, etc.) when relevant

If a PAT is already present in `~/.git-credentials`, you can pipe it to `gh auth login --with-token` to authenticate the gh CLI automatically — no user action needed.

**Why:** The user pointed out (gently, "you dummy you created the repo already lol") that I asked them to `gh auth login` when their machine already had a GitHub PAT stored. Making the user do work I could have done myself adds friction and looks incompetent.

**How to apply:** When a task needs auth'd access to an external service, probe for existing credentials as the *first* step — only escalate to "please log in" if nothing is found. This applies broadly: git hosts, cloud CLIs, container registries, anything requiring tokens.
