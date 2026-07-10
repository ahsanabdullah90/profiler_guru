# Security Policy

For detailed information on Profile Guru's patient data protection guidelines, ethical safeguards, and access controls, please see:

👉 **[Consent Gating & Data Protection](file:///f:/Github/Profile-Guru/docs/consent_gate.md)**

---

## Reporting Vulnerabilities

If you discover a security vulnerability or credentials risk, please do not open a public issue. Log the issue privately or contact the lead maintainer immediately.

Ensure that your local `.env` variables (e.g. `APP_PASSWORD` and `SECRET_KEY`) are generated using cryptographically secure methods, as detailed in **[Installation & Setup](file:///f:/Github/Profile-Guru/docs/setup.md)**.

---

## Known Accepted Risks

### [ACCEPTED] PostCSS XSS — CVE CWE-79 (Moderate, CVSS 6.1)

**Affected package:** `postcss < 8.5.10` (bundled internally inside `next@16.2.9`)  
**Status:** Accepted — not exploitable in this application's deployment model  
**Discovered:** 2026-07-10 via `npm audit`

#### Why the CVE exists
Next.js 16.2.9 ships an internal copy of `postcss` below version 8.5.10. That version has a known XSS vector when it generates CSS from **untrusted user input** and that output is injected as raw HTML.

#### Why it cannot be patched right now
`npm audit fix --force` prescribes a downgrade to `next@9.3.3`, but:
- `next@9.3.3` requires `react@^16.6.0`
- This project runs `react@19.2.4`
- The forced downgrade would break the entire frontend (incompatible peer dependency)

#### Why it is not exploitable here
This application generates no server-side CSS from user input. All CSS is static, authored at build time, and is never rendered as raw HTML. The postcss XSS vector requires **runtime rendering of user-controlled CSS strings**, which does not occur in this codebase.

#### Monitoring condition
This risk will be re-evaluated when:
- Next.js ships a version `>= 16.x` that bundles `postcss >= 8.5.10`, OR  
- The app adds server-side CSS generation from user data

**Next review date:** 2026-10-10

---

## Dependency Audit History

| Date       | Tool       | Findings                              | Action Taken                          |
|------------|------------|---------------------------------------|---------------------------------------|
| 2026-07-10 | `npm audit`| 2 moderate — postcss XSS via next     | Documented as accepted risk (above)   |
| 2026-07-10 | `npm ls`   | 5 extraneous `@emnapi/*` packages     | Cleaned via `npm prune`               |

