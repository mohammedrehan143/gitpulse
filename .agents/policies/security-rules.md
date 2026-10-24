# Policy: Security Rules & Vulnerability Governance

## 1. Secrets Management
1. **Zero Secret Commitment**: Under no circumstances may API keys, personal access tokens (PATs), database passwords, private keys, or secret tokens be hardcoded in code, commit messages, or configuration files.
2. **Environment Variable Injection**: All credentials must be read exclusively from environment variables via `backend/src/gitpulse/common/config.py` using `pydantic-settings`.
3. **Template Preservation**: Keep `.env.example` up to date with dummy placeholder values for every required variable. Never copy production credentials into `.env.example`.

## 2. Ingestion & Webhook Security
1. **GitHub Signature Verification**: All webhook endpoints (`/api/v1/webhooks/*`) must compute HMAC-SHA256 over raw request bodies using the configured secret and verify against the `X-Hub-Signature-256` header using constant-time comparison (`hmac.compare_digest`).
2. **SSRF Prevention**: URL inputs for repository webhooks or custom endpoints must be validated against a strict internal IP blacklist (disallowing `127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16`, AWS metadata `169.254.169.254`).
3. **Payload Sanitization**: Reject payloads exceeding 25MB before parsing to defend against memory exhaustion and ReDoS attacks.

## 3. Database & SQL Protection
1. **Parameterized Queries**: Never construct SQL queries using string formatting, f-strings, or string concatenation.
2. **SQLAlchemy ORM Exclusivity**: Utilize SQLAlchemy 2.0 type-safe expressions or parameterized `text()` constructs.
3. **Least Privilege DB Users**: Application services must connect using credentials limited to DML operations (`SELECT`, `INSERT`, `UPDATE`, `DELETE`). DDL operations are restricted to migration execution.

## 4. Frontend & Web Security
1. **Content Security Policy (CSP)**: Prohibit inline scripts and unsafe evals.
2. **CORS Restrictions**: Do not allow wildcard `*` origins in production environments. Restrict origins to approved dashboard hosts.
3. **Sanitized Rendering**: React default escaping must be preserved. Avoid `dangerouslySetInnerHTML`.
