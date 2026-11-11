---
name: init
description: "Set up a repository for the AI-native SDLC: copies the document templates, seats, config, review rules, CI workflows, eval and monitoring scaffolds. Use once per project."
---
# Set up a project

Run the setup script from the repository root and show its output:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init.py"
```

It never overwrites an existing file. Afterwards, tell the person the three things only they can do:
1. Turn on branch protection for the default branch: require a pull request, require the `stage-check` status, require code owner review.
2. Add `ANTHROPIC_API_KEY` to the repository secrets for the CI jobs.
3. Put their name in `sdlc/seats.json` and `CODEOWNERS`.

Then start with the five parts that need nothing first: `CLAUDE.md`, plan mode, the feedback loop, the hooks (already active), and capturing the first intent.
