# ai-native-sdlc

A Claude Code plugin that runs a software lifecycle in six stages, where each stage leaves a document the next one reads and no stage starts before the previous one is accepted.

It is an independent implementation of the method described in [The AI-native SDLC playbook](https://claude.com/resources/articles/the-ai-native-sdlc-playbook) by Louis Claxton, Anthropic. It is not published or endorsed by Anthropic. The playbook describes the method for large organizations; this plugin packages it so that one person can run it, and a team can grow into it.

## The chain

| Stage | Output | Opens when |
|---|---|---|
| 1 Plan | `intent/<name>/intent.md` | Someone has an idea, a ticket or a finding |
| 2 Design | `intent/<name>/spec.md` | The intent is on the default branch |
| 3 Build | `intent/<name>/plan.md`, then code | The spec is on the default branch, and the plan has an acceptance record |
| 4 Test | Test output, eval results | The coding agent reports done |
| 5 Deploy | A reviewed pull request, a release | Tests and the stage check pass |
| 6 Maintain | A new `intent.md` | A band is breached or a new item arrives |

"Accepted" has one meaning for documents: the file is on the default branch, which it reaches only through an approved pull request. A plan is accepted through a record that pins its content; editing the plan afterwards voids the record.

## What holds the order

| Layer | Where | What it does |
|---|---|---|
| Hooks | Inside the agent, before every write and shell command | Stage lock, protected paths, test lock, credential filter, production gate, acceptance gate |
| Stage check | CI, on every pull request | Fails a pull request that skips a stage, edits a plan after acceptance, or edits an existing test on a fix branch |
| Branch protection | GitHub | Nothing reaches the default branch without an approved pull request |

## Seven seats

Each role has an approval seat. `sdlc/seats.json` says who sits in it and how:

| Setting | Meaning |
|---|---|
| `human` | The role agent reviews first; the named person approves |
| `human-when-flagged` | The role agent passes clean work and escalates anything flagged |
| `agent` | The role agent approves |

One person can hold all seven. Two rules are not configurable: the agent that wrote a piece of work cannot approve it, and the release manager seat is always human.

A change is flagged when it touches a path under `risk_paths` in `sdlc/config.json`, adds a dependency, changes a public API or data model, or conflicts with a policy skill.

## What is in the box

- **Agents (11):** seven role agents (`product-owner`, `policy-owner`, `tech-lead`, `platform-engineer`, `code-owner`, `release-manager`, `service-owner`), the `designer`, and three subagents (`researcher`, `simplifier`, `verifier`).
- **Skills (5):** `/ai-native-sdlc:init`, `:intent`, `:spec`, `:plan`, `:pr-babysit`.
- **Hooks (3 scripts, 6 gates):** see the table above.
- **Project templates:** `CLAUDE.md`, `REVIEW.md`, `CODEOWNERS`, the three document templates, starter policy skills, seat and config files, six CI workflows, an eval scaffold and a detection script.

## Install and set up

```bash
claude plugin marketplace add /path/to/ai-native-sdlc
```

```bash
claude plugin install ai-native-sdlc@ai-native-sdlc-local
```

Then, in the project repository, run `/ai-native-sdlc:init`. It copies the templates and never overwrites an existing file. Three things only you can do afterwards:

1. Turn on branch protection for the default branch: require a pull request, the `stage-check` status and code owner review.
2. Add `ANTHROPIC_API_KEY` to the repository secrets if you enable the CI jobs that call Claude.
3. Put your name in `sdlc/seats.json` and your handle in `CODEOWNERS`.

## A first change, start to finish

1. `/ai-native-sdlc:intent` and describe the problem. Merge the intent pull request.
2. `/ai-native-sdlc:spec <name>`. On a new project the spec includes a Technology choice section; the tech lead seat accepts it and the result goes into `CLAUDE.md`. Merge the spec pull request.
3. `/ai-native-sdlc:plan <name>` on a `change/<name>` branch. When the plan is accepted, the stage lock opens for code.
4. Implement, run the checks, open the pull request, `/ai-native-sdlc:pr-babysit`.
5. Approve and merge. Authorize the release.

Small, well-bounded fixes use a `fix/<name>` branch: they need an accepted plan but no intent or spec, and committed tests cannot be edited.

## Who decides the language and stack

The intent's Constraints section states what the team can review and afford. The designer proposes options in the spec's Technology choice section. The tech lead seat accepts. The platform engineer agent then drafts the Conventions section of `CLAUDE.md`, and every later session follows it.

## What has been tested, and what has not

Tested, by `python3 -m unittest discover -s tests` (18 tests against throwaway git repositories): the stage lock across the full chain and the fix lane, protected paths, the test lock, the credential filter, the production gate, the acceptance gate for each seat setting, the stage check, seat validation, the detection script and the setup script.

Not tested: the agents and skills in a live Claude Code session, and the six CI workflows on GitHub. The workflows other than `stage-check.yml` are marked as untested scaffolds; run each step by hand first.

Known limits:
- Hooks fail open: if a hook script crashes, the tool call proceeds. The stage check in CI is the backstop.
- The shell check for protected files is best effort; a determined command can get past it. Branch protection and `CODEOWNERS` are what actually protect those files.
- GitHub does not count an author's approval of their own pull request. Pull requests the CI jobs open are authored by the workflow identity, so you can approve them. For pull requests you open yourself as a solo maintainer, require the status checks and merge by hand.
- Managed settings, a first responder in an incident channel, and mapping to an existing ticket system are out of scope.

## Requirements

Claude Code with plugin support, Python 3.9 or later, git.

## License

MIT. The method is described in The AI-native SDLC playbook; all text and code here are this project's own.
