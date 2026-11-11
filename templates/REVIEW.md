# Review instructions

## Passes
Run three passes and tag each finding with its pass:
- Bugs: logic errors, broken edge cases, regressions
- Security: injection, missing authentication or authorization, personal data in logs
- Compliance: the change matches spec.md and plan.md, and the promised proof is present

## What Important means here
Important is for findings that would break behavior, leak data or breach a policy. Style and naming are nits.

## Cap the nits
Report at most five nits per review; summarize the rest as a count.

## Do not report
Generated files and anything CI already enforces.
