# Architecture overview

`passwords_otp` is an independent Nextcloud application with its own navigation entry, PHP controller and compiled assets. The **Vue edition** uses Vue 3 and Nextcloud Vue components. The unreleased source uses a Passwords dependency service and a prerequisite migration. There is **no separate OTP database or OTP data-schema change**; Nextcloud maintains normal migration/job bookkeeping.

## Request and data flow

1. A valid Nextcloud browser session is required for the page and a CSRF-protected, non-cacheable bootstrap POST. Initial page state contains URLs and a session fingerprint, not the Passwords token.
2. The dependency service verifies Passwords installation, global enablement, matching supported versions and the required methods before the PHP adapter acquires credentials. Per-user authorization is checked separately. The adapter still uses Passwords' internal `ApiTokenHelper` and `EnvironmentService`, checking authenticated user context and impersonation.
3. The browser controller validates the same-origin HTTPS configuration, creates the pinned upstream client, clears the bootstrap credential references and opens the original Passwords API session.
4. The domain session completes supported vault/CSE challenges, reads the idle policy, and parses compatible `client.ios.otp` records. It imports non-extractable WebCrypto keys; only public account metadata leaves the session snapshot.
5. A framework-independent `TotpPresenter` controls code windows, session proofs, the local countdown and copying. The Vue list renders its display snapshots.
6. Creating an entry requires an explicit save action, fresh authorization, field validation, the existing one-use API permit, exactly one attempted create operation, and readback verification. An uncertain result blocks retries until a new session.

The interface has no operation for updating or deleting existing records and no HOTP counter-write flow. Manage sharing and subsequent changes through the original Passwords app.

## Source orientation

| Location | Responsibility |
| --- | --- |
| `templates/main.php`, `src/main.js` | Small PHP mount point, initial-state consumption and Vue application startup |
| `src/App.vue` | Nextcloud application layout, status presentation, component composition and lifecycle event wiring |
| `src/components/` | Vault authentication, OTP account list, and new-entry dialog using Nextcloud Vue controls |
| `src/ui/controller.mjs` | Framework-independent startup, unlock, create, error and page-lifecycle orchestration |
| `src/ui/dom-safety.mjs` | Small scoped, synchronous erasure boundary before Vue's queued rendering or a BFCache snapshot |
| `src/ui/messages.mjs` | Finite public error vocabulary; arbitrary upstream exception text is not rendered |
| `src/ap1/` | Existing bootstrap, transport, upstream client and domain-session implementation |
| `src/ap2/` | OTP parsing, safe public metadata, search and list notice text |
| `src/ap3/totp.mjs` | Existing local WebCrypto TOTP calculations |
| `src/ap3/ui.mjs` | DOM-independent `TotpPresenter`, time/authorization guards and trusted-click clipboard operation |
| `src/ap9/` | Nextcloud browser-session/fingerprint verification |
| `src/ap12/` | Existing API route allowlist, input validation and create-once domain behavior |
| `lib/` | Dependency migration and runtime guard, legacy job cleanup, controller/CSP/asset loading and isolated Passwords token adapter |
| `vite.config.js`, `scripts/release.py`, `scripts/appstore_package.py` | Compilation, exact output inventory, dependency notices, checked ZIP/TAR construction and explicit signing gates |

The historical `ap*` names identify implementation work packages, not release versions or a deployment sequence. They remain on unchanged domain modules to avoid unnecessary changes to authentication and cryptography.

## Passwords dependency lifecycle

First registration uses a no-schema migration to reject an unavailable Passwords
dependency. The controller, bootstrap and session-status routes use the
request-time guard. App activation and group scope survive an unavailable
dependency. If a legacy scheduled job runs, it removes its old registration.
Read [dependency lifecycle](DEPENDENCY_LIFECYCLE.md) for the published 1.1.3
behavior and current rules.

## Vue and sensitive state

The controller owns the inactivity deadline and enforces it before updating protected content or starting guarded operations. It clears the UI and invalidates the vault immediately on expiry. The controller and session objects are plain closures/classes. They are not placed in `reactive()`, a deep Vue proxy, Pinia, a router store or persistent browser storage. The domain classes retain native private fields for keys and state. `App.vue` uses a shallow reference to public display state; this includes short-lived displayed OTP codes, but not the underlying OTP seed, WebCrypto key, upstream client or token.

Form components necessarily hold short-lived input values. Passwords, master passphrases, secondary codes and setup secrets are cleared on submission, closing, hiding, teardown and terminal failure paths. The controller copies request values into its own short-lived request object before clearing the caller's form object, then clears those values in `finally` blocks. JavaScript reference clearing is not a guarantee of physical memory erasure by the browser.

Vue batches DOM updates. `clearSensitiveDom()` therefore synchronously erases displayed codes and secret inputs and hides protected app content on revocation/navigation. Its selectors are restricted to this app and its explicit dialog portal. State-driven Vue rendering performs normal teardown; the helper does not remove Vue-managed nodes. A render-revision signal repairs the view if the next authorized code happens to equal the cleared value.

## Preserved OTP and session invariants

- One presenter owns the clock/cache for the authorized snapshot; row components do not independently perform authorization requests.
- New mandatory 30-second windows, individual account-period boundaries, backward time changes, visibility restoration and focus changes require appropriate session verification.
- Asynchronous verification is bound to its request start and generation. A delayed response or HMAC completion cannot authorize a later window or revive a terminated session.
- Search changes visibility without resetting authorization or recomputing valid codes. Hidden search results cannot be copied.
- Clipboard invocation remains synchronous within the user's copy action, with a fresh validity check and at least **2.5 seconds** remaining. Leading zeroes are preserved as strings.
- Page navigation and BFCache restoration clear local sensitive state and require reload; upstream server-session closure remains best effort.

`NcDialog` uses the application's explicit action buttons, blocks close while saving, and disables this dialog's entrance/exit transitions to avoid delayed focus-trap activation during rapid navigation. A small keyboard guard provides immediate containment, including a focused busy status. Its dedicated portal is placed at body level so the real Nextcloud header cannot cover the modal. Form Enter does not implicitly create an entry; Enter or Space on **OTP speichern** remains available. The displayed code itself remains non-interactive, as requested feature #7 is outside this migration.

## Build and release boundaries

Vite compiles the Single File Components to exactly **`js/app-120-dev.mjs`** and **`css/app-120-dev.css`**. PHP loads the JavaScript as an ES module. Dependencies are bundled locally; there is no runtime CDN, router requirement or Node.js service.

The build writes `.build/bundle-modules.json` with actual module inputs, hashes of both output assets, production mode and a complete hash inventory of `src/`, `package.json`, `package-lock.json` and `vite.config.js`. Changes during compilation or after compilation invalidate the candidate. External runtime imports and application inputs outside `src/` are rejected, including browser-test fixtures. The release script cross-checks these against the explicit license inventory, permits only the fixed runtime file set, and constructs deterministic ZIP and TAR archives with the same `BUILD.json` and complete third-party notices. Archive checks also enforce size limits, safe paths, no symlinks, file hashes and a source-commit identity. Packaging requires a clean committed checkout.

This source includes the `appinfo/info.xml` bugs URL identified in PR #5. Reviewed TAR/signing preparation incorporates and corrects the draft PR #9 approach: Nextcloud 35 signature hashes use relative paths without leading slashes. The signed path requires the exact runtime files, cryptographic verification and a real Nextcloud certificate-trust check. Ordinary GitHub artifacts remain unsigned; historical tags/assets are unchanged. See [App Store packaging](APPSTORE_PACKAGING.md).

See [Third-party notices](../THIRD_PARTY_NOTICES.md), [Development](DEVELOPMENT.md) and the [migration report](NEXTCLOUD_VUE_MIGRATION.md).

## Unchanged security boundaries

The upstream WebUI bearer token is broader than this app's operations; client-side route restrictions cannot narrow its server-side scope. Passwords and TOTP seeds in one vault are not independent factors against vault compromise. Browser extensions, clipboard history and same-origin compromise remain relevant, and internal upstream Passwords APIs can change on upgrades.

See [Security review](SECURITY_REVIEW.md) and [Security Policy](../.github/SECURITY.md). The UI framework change does not resolve these architectural limits.
