---
name: spec
description: "Produce the requirements and design spec for an accepted intent. Use after intent.md has merged, to write intent/<name>/spec.md."
---
# Write the spec

Stage 2, Design. The input is an accepted `intent/<name>/intent.md`; the output is `intent/<name>/spec.md` beside it.

1. Confirm the intent is on the default branch. If it is not, stop: the stage lock will refuse the write.
2. Run the `designer` agent with the intent path. It loads the policy skills and writes the spec from `${CLAUDE_PLUGIN_ROOT}/templates/intent/spec.md`.
3. Run the `product-owner` agent on the spec. If the spec has flagged concerns or touches a risk path, also run the `policy-owner` agent.
4. If the spec has a Technology choice section, run the `tech-lead` agent on that section.
5. Show the flagged concerns first. They are resolved with the owner of each rule before engineering sees the spec.
6. Open the spec as a pull request. The product owner seat accepts it by merging; that is what opens Build.

Change name: $ARGUMENTS
