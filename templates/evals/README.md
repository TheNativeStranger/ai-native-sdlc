# Agent evals

Each file in this folder is one eval: a prompt plus the checks that define an acceptable result. Collect twenty to fifty real tasks from recent work. A new project starts with the two samples here and adds one eval per merged change and one per production incident.

`check.sh <eval.json> <result.json>` exits non-zero when the result fails. The suite runs nightly and on every change to CLAUDE.md, a skill or a hook.
