# Security design and residual risks

This is a technical overview, **not** a substitute for the [vulnerability reporting policy](../.github/SECURITY.md).

## Scope and authentication

passwords_otp is an unofficial companion to the existing Nextcloud Passwords app. It does not modify the Passwords source or hold a separate vault. Page access requires an authenticated Nextcloud session; an authenticated CSRF-protected bootstrap POST obtains the necessary upstream client credential **after** page load, rather than embedding it directly in initial HTML.

The browser necessarily uses the **original Passwords WebUI bearer credential**. Its upstream privileges are broader than reading TOTP codes or creating an entry. A compromised browser, extension or same-origin script may abuse this credential. The JavaScript request allowlist and create-once authorization logic **do not provide server-side privilege reduction**. The limited AIO pilot operator explicitly accepted this remaining risk; it is not eliminated or generally approved.

## OTP and session controls

- TOTP is computed locally using WebCrypto from compatible Passwords records. Only validated TOTP fields are used; HOTP and invalid fields are not misrepresented as TOTP.
- Existing short but syntactically valid legacy Base32 secrets can be read (5 bytes minimum); newly entered secrets must be at least 10 bytes, which is still shorter than the 160-bit RFC 4226 recommended key.
- Before each new 30-second slot and on focus, server-side Nextcloud session validity is checked. A failed or stale check must not allow new codes. A code from the currently verified slot may remain visible until it expires, and already copied codes cannot be revoked.
- Passwords API sessions may expire independently of the Nextcloud login. Before opening the create dialog and before writing, session/request is checked. HTTP 403/429 is treated as an API access/rate-limit error, not necessarily an expired Nextcloud login.
- A wrong Passwords CSE master passphrase is only retried for the known upstream **HTTP 401 / ab6e13ba** response. Unrecognized failures, including **HTTP 500 / 033d1943**, are not silently treated as user typing errors.
- On pagehide, local OTP state is immediately cleared; closing the upstream session is best-effort only.

## Data modification

The UI only creates new Passwords entries; it cannot edit or delete existing ones. New records are validated, sent once and checked by readback. An uncertain POST acknowledgement is not automatically retried, to avoid duplicate entries. Client-side allowlists remain defense in depth, not a true permission boundary.

Passwords and OTP secrets stored in the same vault may be compromised together. System clipboards, extensions, local time accuracy and users' device security also matter.

## Operations and compatibility

The supplied AIO installer verifies archive hashes and source identity, restricts scope to an existing group, and provides a fail-closed first-install path. It does not upgrade an existing OTP app. Rollback normally requires the exact recorded installation; emergency disable after an AIO update still requires the same persistent app volume, original receipt and unchanged own files, and does not restore database state.

The PHP adapter uses **internal, potentially unstable Passwords interfaces** (ApiTokenHelper, EnvironmentService). Newer upstream versions must be tested independently. No general third-party production certification, App Store signing or security audit is claimed.

Please report vulnerabilities privately. Do not publish credentials, OTP setup keys, tokens or raw network requests.
