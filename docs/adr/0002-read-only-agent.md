# ADR 0002: Read-only, comment-only agent

Status: proposed. Date: 2026-10-06.

## Context

The agent reads untrusted PR content. If it could write files, run code, or reach the network, a prompt injection could do real damage.

## Decision

- The GitHub App has Metadata read, Contents read, and Pull requests write. Nothing else.
- The agent has four tools: `read_file`, `search_repo`, `view_diff_hunk`, `list_related_tests`. All read-only.
- No shell, no network, no file writes.
- Output must match a strict schema; anything else is dropped.
- Hard caps on steps, tokens, comments per PR, and daily spend.

## Consequences

- DiffMate cannot auto-fix code. This is a deliberate non-goal.
- Worst case from a successful injection is a bad or missing comment, not data loss or exfiltration.
- Easy to explain in interviews and to test with planted-instruction PRs.
