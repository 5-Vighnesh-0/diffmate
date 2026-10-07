# Threat Model

Status: draft. Review against the code at the end of Phase 3.

Method: STRIDE-lite. For each asset, list what can go wrong and the planned control.

## Assets

- GitHub App private key and installation tokens
- Webhook secret
- LLM API key and the spend it controls
- Repository code the agent reads (private repos included)
- Findings and trace data in Postgres
- Dashboard sessions

## Trust boundaries

1. GitHub to API (webhooks): untrusted until the signature is verified.
2. PR content to agent: always untrusted data, even from "trusted" authors.
3. Browser to dashboard API: untrusted until authenticated and authorized.
4. Worker to the internet: only GitHub API and the LLM provider.

## Threats and controls

| # | Threat | Control | Test |
| --- | --- | --- | --- |
| 1 | Forged webhook | Verify `X-Hub-Signature-256` with constant-time compare; reject with 401 | Bad and missing signature tests |
| 2 | Replayed webhook | Remember `X-GitHub-Delivery` IDs; ignore repeats | Replay test |
| 3 | Oversized payload (DoS) | Body-size limit (413), per-IP rate limit | Large-body test |
| 4 | Prompt injection via PR title, description, code, or comments | Label all PR content as untrusted data; read-only tools; strict output schema; drop invalid output | Planted-instruction PRs in the security suite |
| 5 | Agent exfiltrates data | No network, shell, or write tools; worker egress allowlist | Tool-list test; egress check |
| 6 | Cost abuse (many PRs, huge diffs) | Step and token caps; diff size cap; daily spend limit pauses new runs | Cap tests |
| 7 | Comment spam | Max 5 comments per PR; one run per commit SHA | Filter test |
| 8 | Leaked GitHub App key or LLM key | Env or secret file only; never logged or committed; gitleaks in CI; rotation runbook | gitleaks; see `runbooks/rotate-secrets.md` |
| 9 | Over-broad GitHub permissions | Metadata read, Contents read, Pull requests write only | Manual check at app setup |
| 10 | Long-lived tokens | JWT to short-lived installation token, fetched per run | Unit test on token use |
| 11 | Dashboard IDOR (reading another installation's runs) | Every query filtered by the user's installations; 404 not 403 | Cross-tenant access tests |
| 12 | CSRF on feedback and logout | CSRF token plus SameSite=Lax cookie | CSRF test |
| 13 | Session theft | httpOnly, Secure, SameSite=Lax cookies; short expiry | Cookie flag test |
| 14 | XSS in dashboard (finding text is LLM output) | Render as text, never as HTML; CSP header | Render test with script payload |
| 15 | SQL injection | Parameterized queries via SQLAlchemy only | Lint rule; review |
| 16 | Secrets or code in logs | Structured logs with run ID only; no diffs | Log review |
| 17 | Supply chain (packages, installed skills) | pip-audit, npm audit, lockfiles; skills installed only after approval and quality gate | CI audits |

## Out of scope for v1

Multi-tenant billing abuse, compromised GitHub itself, compromised LLM provider, and physical access.

## Residual risk

Prompt injection cannot be fully eliminated. The design limits the damage: the agent can only read and comment, and every output is schema-checked.
