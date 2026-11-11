---
name: pr-babysit
description: "Carry a pull request to the point where it waits only on a person's approval: review it, address comments and failing checks, push fixes."
---
# Carry the pull request to the gate

Stage 5, Deploy. Findings inform the merge; they never approve it.

1. Run the `code-owner` agent on the pull request. It must not be the session that wrote the code; if this session did, say so and stop after step 2.
2. Collect unresolved review comments and failing checks.
3. Address each one and push the fix. Never weaken a test or a check to make it pass.
4. Repeat until the checks are green and nothing is unresolved.
5. Stop. The code owner seat approves and merges. If the same mistake was found for the second time, propose the line for `CLAUDE.md`.

Pull request: $ARGUMENTS
