# Architecture overview

This is an **independent Nextcloud application**, installed as passwords_otp, with its own navigation entry, PHP page/controller and static JavaScript/CSS assets.

1. A valid Nextcloud browser session is required for the page and a CSRF-protected, non-cacheable bootstrap POST.
2. The PHP adapter uses the official Passwords app's internal ApiTokenHelper and EnvironmentService, with checks for authenticated user context and impersonation.
3. The browser-side client authenticates to the **original Passwords API** using the upstream WebUI token. It performs Passwords challenges/CSE handling and retrieves permitted vault entries.
4. The browser parses compatible client.ios.otp fields and imports keys into WebCrypto to derive RFC 6238 TOTP codes.
5. Before each new code time window and on focus, a Nextcloud session check must succeed. Unavailable/expired auth causes a fail-closed state.
6. Creating an OTP entry requires user action, another authorization check, strict field validation, one Passwords API create POST and readback verification.

There is **no separate OTP database**; the app uses the original Passwords records. The UI intentionally has no update/delete functionality for existing entries, and there is no HOTP counter-write operation.

## Source code orientation

The `ap*` directory names are historical internal work-package identifiers, not different release versions or supported components. For this project's v1.0.0 tree:

| Location | Responsibility |
| --- | --- |
| `src/ap1/` | Browser entry point, bootstrap, upstream Passwords API client wiring, network/session lifecycle |
| `src/ap2/` | TOTP record parsing, sanitization and view rendering |
| `src/ap3/` | WebCrypto TOTP calculation and desktop interaction/controller |
| `src/ap9/` | Nextcloud browser-session and fingerprint verification |
| `src/ap12/` | Passwords API route allowlist, validation and create-once flow |
| `lib/AppInfo/`, `lib/Controller/`, `lib/Service/` | Nextcloud registration, CSRF/session-protected PHP pages and Passwords token adapter |
| `tests/` | JavaScript contracts, real upstream client fixtures, Python packaging/deployment tests, PHP security checks and synthetic Chromium tests |

These names are kept stable to avoid code churn in a tested release. They are not an installation sequence.

## Security boundaries

- The upstream **WebUI bearer token is more privileged than read-only TOTP**. Client request allowlists do not reduce its server-side privileges.
- A valid original Passwords vault and a service's second-factor seed held together are **not independent security factors** on vault compromise.
- Browser JavaScript, clipboard history, extensions and compromised same-origin scripts remain relevant attack surfaces.
- A browser pagehide cannot guarantee immediate closure of the upstream server session.
- Internal Passwords integration points may break on upstream upgrades.

See [Security review](SECURITY_REVIEW.md) and [Security Policy](../.github/SECURITY.md).
