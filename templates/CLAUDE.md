# <Project name>

## Commands
- Build: <one command>
- Test: <one command; exits non-zero on failure>
- Lint: <one command>

## Conventions
- <Language and framework, once the technology choice is accepted.>
- <The rules that matter. Keep this short.>

## Architecture
- <Where things live.>

## Lifecycle
Work moves through six stages and each leaves a document: intent/<name>/intent.md, spec.md, plan.md, then code, review and release. A document is accepted when it is on the default branch; the plan is accepted through an acceptance record. Hooks refuse writes that skip a stage. Do not work around a refusal: finish the earlier stage.

## Verifying your work
Run build, test and lint before reporting any task complete, and paste the output. If a test fails, fix the code, not the test.

## Things Claude gets wrong
- <Add a line here the second time the same mistake is made.>
