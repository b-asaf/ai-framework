---
name: clean-code-security
description: Use when reviewing or implementing code that handles external input, authentication, persistence, or external services — applies OWASP Top 10 checklist. All security findings are BLOCKING.
---

# Clean Code — Security (OWASP Top 10)

Security findings are always **BLOCKING**. There is no such thing as a non-blocking security issue in production code.

`[SECURITY/<category>] <file>:<line> — <what the vulnerability is and why it is dangerous>`

---

## Review checklist — work through each category for every changed file

### A01 — Broken Access Control
- Is every endpoint/action gated by an authorization check?
- Are authorization checks enforced server-side, never in client-controlled data?
- Can a user access or modify another user's resources by changing an ID in a request?
- Are directory traversal paths possible via user input?

### A02 — Cryptographic Failures
- Is sensitive data (passwords, tokens, PII, secrets) ever logged, stored in plaintext, or included in error messages?
- Are passwords hashed with a memory-hard algorithm (bcrypt, argon2, scrypt)? Never MD5, SHA-1, or unsalted SHA-256.
- Are secrets hardcoded in source or config files committed to version control?
- Is HTTPS enforced for all external data transmission?

### A03 — Injection
- Is any user-controlled input concatenated into a SQL query, shell command, XML, LDAP expression, or template string?
- Are parameterised queries / prepared statements used for all database access?
- Is `eval()`, `exec()`, or equivalent used anywhere with externally influenced data?
- Are file paths constructed from user input without sanitisation and path canonicalisation?

### A04 — Insecure Design
- Does the design assume clients are trustworthy? (e.g. rate limiting only on the frontend)
- Is there a mechanism to limit authentication attempts (brute-force protection)?

### A05 — Security Misconfiguration
- Are default credentials, sample accounts, or debug endpoints present in production code paths?
- Are verbose error messages, stack traces, or internal paths returned to the client?
- Are CORS origins set to `*` in non-public APIs?
- Are security headers set (Content-Security-Policy, X-Frame-Options, X-Content-Type-Options)?

### A06 — Vulnerable and Outdated Components
- Are deprecated APIs or libraries used that have known security advisories?
- *(Full dependency audit is handled by the `xray-scanning` skill and JFrog Xray — flag only what is visible in the changed files.)*

### A07 — Identification and Authentication Failures
- Are session tokens / JWTs validated on every authenticated request (signature, expiry, audience)?
- Are session IDs regenerated after login (session fixation protection)?
- Are failed authentication attempts logged?

### A08 — Software and Data Integrity Failures
- Is deserialisation of user-controlled data performed without type constraints?
- Are integrity checks (HMAC, signature verification) applied to data received from external systems?

### A09 — Security Logging and Monitoring Failures
- Are security-relevant events logged (auth success/failure, authorisation failures, privilege escalations)?
- Does any log statement include sensitive data (passwords, tokens, PII)?

### A10 — Server-Side Request Forgery (SSRF)
- Does any code fetch a URL derived from user input?
- If yes: is the target URL validated against an allowlist of permitted destinations?

---

## Write-time checklist

Before submitting any implementation that handles external input, authentication, or persistence:
- [ ] No user input touches a query, command, path, or template without parameterisation or strict allowlist validation
- [ ] No secret, credential, or sensitive value is hardcoded or logged
- [ ] Every state-changing action is authorised server-side
- [ ] Passwords use a memory-hard hash; tokens are validated on every request
- [ ] Error responses reveal no internal paths, stack traces, or system details
- [ ] User-controlled URLs are validated against an allowlist before fetching
- [ ] Deserialised data from external sources is constrained to known-safe types
