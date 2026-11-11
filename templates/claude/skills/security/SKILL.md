---
name: security
description: "The project's security rules. Use when writing or reviewing a spec, a plan or code that touches them."
---
# Security

Starter rules. Replace them with your own; the policy owner seat signs off every change to this file.

1. Every external-facing route requires authentication; nothing anonymous outside a health check.
2. Validate input against a schema and reject unknown fields.
3. Never log secrets, tokens or personal data.
4. Secrets come from the environment, never from the repository.
5. A new dependency is a flagged change: name it, its license and why it is needed.

When a rule cannot be met, or two rules contradict each other, say so under Flagged concerns. Do not pick a side quietly.
