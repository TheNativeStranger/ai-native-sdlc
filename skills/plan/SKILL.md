---
name: plan
description: "Start building a change: write and agree the implementation plan before any code. Use after spec.md has merged."
---
# Plan, then build

Stage 3, Build. Nothing is implemented without an accepted plan.

1. Work in plan mode. Create the branch `change/<name>` (or `fix/<name>` for a small, well-bounded fix).
2. Read `intent/<name>/intent.md` and `spec.md`. Use the `researcher` agent for questions that need many files read.
3. Write `intent/<name>/plan.md` from `${CLAUDE_PLUGIN_ROOT}/templates/intent/plan.md`: Files that change, Order of work, Risks, Proof. An engineer who never saw this conversation should be able to implement from it.
4. Run the `tech-lead` agent on the plan and revise until its verdict is `PASS` or it flags the plan for a person.
5. The tech lead seat accepts the plan. The agent records it when the seat's setting allows; otherwise the person runs `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/accept.py" plan <name>` in their own terminal. Until then the stage lock refuses code.
6. Implement in the order the plan gives. If the work departs from the plan, update `plan.md` in the same commit and have it accepted again.
7. For a bug fix, write the failing test first and commit it before touching the code. On a fix branch a committed test cannot be edited.
8. Before reporting done: run the test, build and lint commands from `CLAUDE.md` and show the output, then run the `verifier` agent.

Change name: $ARGUMENTS
