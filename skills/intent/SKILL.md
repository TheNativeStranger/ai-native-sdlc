---
name: intent
description: "Capture an idea as intent/<name>/intent.md. Use when someone describes a problem, a feature idea, a ticket or an incident that should become work."
---
# Capture an intent

Stage 1, Plan. The output is `intent/<name>/intent.md`, written in the originator's own terms.

1. Ask the originator to describe the problem in their own words: what they cannot do today, who is affected, what better looks like, what is out of scope. No formal language is needed.
2. Ask what an analyst would ask until the idea is concrete: scope, users, constraints, what success looks like. Ask about constraints the build will need: languages the team can review, budget, hosting, rules that apply.
3. Pick a short kebab-case `<name>`. Copy `${CLAUDE_PLUGIN_ROOT}/templates/intent/intent.md` to `intent/<name>/intent.md` and fill in every section.
4. Show the result and ask the originator to correct anything you misunderstood.
5. Run the `product-owner` agent on the file and show its findings.
6. Open the intent as its own pull request. The product owner seat accepts it by merging. Design does not start before that; a hook enforces it.

Topic, if given: $ARGUMENTS
