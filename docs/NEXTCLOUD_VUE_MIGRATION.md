# Nextcloud Vue migration — implementation report

**Scope:** variant B, complete migration of the presentation layer with local quality gates. **Candidate:** 1.1.0. **Date:** 2026-11-19. The [validation record](VALIDATION_VUE_1.1.0.md) identifies the tested source, environment, results and limitations.

The application now uses **Vue 3.5.45**, **@nextcloud/vue 9.14.1** and a pinned **Vite 7.3.8** build. The old imperative application entry and handwritten widget rendering have been replaced. Authentication, the Passwords client, CSE handling, OTP parsing/cryptography, browser-session verification and the create-once domain operation retain their existing security boundaries. No data conversion, database migration or change to stored Passwords entries is needed.

Nextcloud's [JavaScript standards](https://docs.nextcloud.com/server/stable/developer_manual/getting_started/coding_standards/javascript.html) recommend Vue for app interfaces; this recommendation alone was not treated as proof that the old UI was defective. The migration instead addresses concrete integration, maintainability, accessibility and lifecycle requirements. The [Nextcloud Vue library](https://github.com/nextcloud-libraries/nextcloud-vue) supplies the controls; the application's authorization and secret-handling behavior remains its own responsibility.

## 1. Delivered interface

| Area | Implementation | Result |
| --- | --- | --- |
| Application shell | `NcContent`, `NcAppContent`, one main content landmark and a page heading | Layout uses the Nextcloud app shell and theme variables |
| Vault unlock | `NcPasswordField`, `NcSelect`, `NcTextField`, `NcButton` | Master-key and supported second-factor challenges retain the actual pinned client |
| Status and failures | `NcNoteCard` with finite, application-owned messages | Loading, success, retry and terminal errors have explicit visual and live-region states |
| Search and accounts | `NcTextField`, semantic account list, `NcEmptyContent` | Safe text rendering, filtering, empty-state handling and responsive metadata/code layout |
| TOTP display | Output element, native progress and a named `NcButton` | Leading zeroes, period/countdown behavior and the explicit copy action are retained |
| New entry | `NcDialog`, Nextcloud form fields and explicit save/cancel actions | Labels, validation, keyboard containment, focus return and saving state are covered |
| Themes and layout | Nextcloud color/spacing variables, logical CSS properties, scoped rules | Light/dark/custom-theme and narrow-viewport behavior are exercised without global button overrides |

The title, explanation of personal/shared passwords, explicit create operation and the product's German language remain. The interface does not add a second navigation system, counters, a global state store, a manual vault-lock feature or editing/deleting existing entries. Sharing and later edits remain in Passwords. Issues [#6](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/6) (language support) and [#7](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/7) (clicking the displayed code) remain separate feature requests.

### Modal integration

The dedicated dialog host is moved to `document.body` before Vue mounts. In a real Nextcloud 35 page, the fixed `#content` creates a stacking context below the global header; a modal inside that context cannot cover the header even with a high modal z-index. A body-level host gives the standard Nextcloud modal the intended layer. The portal keeps its explicit app-specific ID and German language, and remains part of synchronous sensitive-data cleanup.

The modal's entrance/exit transition is disabled only for this sensitive dialog. Testing found that Nextcloud's delayed focus-trap activation could otherwise race with immediate submit or page navigation. A small key handler protects Tab/Escape during opening; while saving, focus remains on the status and close controls are disabled. Input Enter does not create an entry. Enter/Space on **OTP speichern** remains an explicit keyboard save action.

## 2. Architecture and sensitive state

The implementation separates four responsibilities:

1. **Domain/session modules:** the existing Passwords transport, authentication/CSE, parser, TOTP crypto and create-once operation.
2. **DOM-independent presenter:** `src/ap3/ui.mjs` owns code validity, clock windows, authorization proofs, search visibility and copy behavior.
3. **Application controller:** `src/ui/controller.mjs` coordinates initialization, unlock, create and termination through plain closures.
4. **Vue components:** `src/App.vue` and `src/components/` render public state and accept short-lived form input.

The client, bearer token, domain session and imported WebCrypto keys are never deep-proxied or stored in a reactive global store. Vue receives public account metadata and short-lived displayed codes. Input components necessarily contain short-lived passwords/seeds while the user edits them. Those references and the DOM values are cleared when submitted, closed, hidden, terminated or unmounted. Clearing JavaScript references does not promise physical erasure of immutable strings from browser memory.

`clearSensitiveDom()` is deliberately retained as a small synchronous boundary. Vue normally queues rendering; relying only on a reactive state change would leave a brief interval before secret inputs/codes disappeared, including before a BFCache snapshot. The boundary clears this app's inputs and codes immediately, disables copy controls and hides protected content. It does not remove Vue-owned nodes. Vue then performs normal teardown. A render revision and tiny field directives restore the validated view when a later authorized code equals the previous code exactly.

There are no production test hooks, fake crypto imports, runtime CDN resources or browser-persisted credentials. The existing Passwords client **1.0.0-beta.6117** and libsodium wrapper **0.8.4** remain pinned.

### Preserved authorization and creation rules

- Page/bootstrap requests still require the original authenticated Nextcloud session; the bootstrap POST remains CSRF-protected and non-cacheable.
- Focus/visibility restoration, mandatory 30-second verification windows, account-period boundaries and backward clock changes cannot silently reuse an invalid authorization proof.
- Delayed checks and HMAC completions are tied to a generation and request-start time. They cannot revive a terminated view or authorize a newer window.
- Copy invokes the clipboard API directly from the trusted user action, rechecks code validity and requires at least 2.5 seconds remaining. Search-hidden records cannot be copied.
- Create retains the API route allowlist, fresh access checks, one-use permit, validation, exactly one create attempt and readback verification. An uncertain result does not encourage an automatic retry.
- Pagehide immediately clears local sensitive state. BFCache return stays closed and requires reload; upstream session closure is best effort.
- Arbitrary upstream exception messages, objects and codes are not copied into the public error state. The first terminal cause is preserved when later asynchronous operations complete.

The unchanged core paths are listed in the validation record. PHP changes are limited to candidate metadata, the mount template and asset loading. The migration does not narrow the upstream WebUI token's server-side privileges; [issue #1](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1) and the [security review](SECURITY_REVIEW.md) remain relevant.

## 3. Defects found during migration and verification

| Finding | Correction | Regression evidence |
| --- | --- | --- |
| Reactive rendering could leave codes/secret inputs visible until the next Vue patch | Synchronous, scoped DOM erasure plus component-model clearing | Same-tick, pagehide, revocation and BFCache tests |
| A freshly verified code equal to the cleared code was not necessarily rewritten by Vue | Explicit scrub revision and DOM repair directives, keeping copy-button identity | Identical-code restoration after focus/background changes |
| Initial component errors could occur before the controller was registered with the error handler | Register termination synchronously during setup; guarded fixed-text fallback | Malformed initial shell state causes no authentication request |
| Delayed work could overwrite a terminal/uncertain status or act on a terminated view | Lifecycle generations and first-terminal-state handling | Controller and held-request browser regressions |
| Dialog focus activation could race with fast submit or pagehide | Scoped transition removal, immediate keyboard containment and busy-status focus | Held create, Escape/Tab, duplicate-submit and rapid pagehide cases |
| Real Nextcloud header covered the narrow-screen modal | Body-level dedicated portal | Real-shell modal stacking assertion |
| Nextcloud's global native-progress rule collapsed the countdown bar inside a flex column | App-scoped fixed flex basis and size, retaining native theme colors | Actual bar dimensions checked in the real shell and every list viewport |
| Default password-field behavior could contact the password-strength service | Explicitly disable strength checking and trailing action for these sensitive fields | Browser request allowlist and real workflow checks |
| A package could pair a clean newer source commit with an older frontend build | Complete source-input hashes, production-mode metadata and independent package revalidation | Added/removed/edited input, mode and inventory rejection tests |
| Source could change between initial clean-tree verification and package output | Recheck HEAD and worktree after the two package constructions | Packaging regression tests |
| CSS minification removed the installer's existing build marker | Emit the fixed marker after minification and before output hashing; retain the installer/package rejection check | Initial clean-package rejection followed by verified corrected output and a new clean-source gate |
| Default shared build configuration brought unused vulnerable dependency chains | Minimal explicit Vite configuration and reviewed minimatch override | Full npm audit and production-module inventory |

These findings illustrate why a widget-for-widget replacement alone would not have completed this migration. The additional work concerns actual asynchronous, security and shell-integration behavior.

## 4. Build, dependencies and distribution

The pinned build produces one ES module and one stylesheet:

- `js/app-110.mjs`
- `css/app-110.css`

Nextcloud 35 resolves the `.mjs` asset and emits a module script. All runtime dependencies are bundled; the installed app does not require Node/npm. The build is approximately **1.08 MB JavaScript and 62.5 kB CSS** before transfer compression (about **364 kB + 10 kB gzip**). This is a measurable dependency cost of adopting the component library. No unmeasured claim of faster startup is made. Code splitting was deliberately avoided for the fixed, verifiable two-asset distribution.

The explicit Vite configuration uses the official Vue plugin and keeps the Vue Options API enabled because the pinned Nextcloud components require it. Production devtools are disabled. Only the approved source/dependency paths and known virtual helpers may contribute modules. External runtime imports and additional assets fail the build.

The broader shared Vite preset was evaluated, but its unused Node-crypto polyfill chain introduced the unpatched `elliptic` advisory [GHSA-848j-6mx2-7j84](https://github.com/advisories/GHSA-848j-6mx2-7j84). That dependency chain was removed by using the small explicit configuration. The transitive minimatch version is pinned to **11.0.9**, beyond the affected range of [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249). The complete locked dependency tree passes `npm audit --audit-level=low` with no reported advisories at the time of verification. This is a time-bound advisory result, not a proof that dependencies have no defects.

### License and package integrity

`scripts/runtime-licenses.json` records the locked production dependency closure and original notices. Missing npm-distributed notices are supplied from the exact reviewed upstream revisions under `licenses/npm/`, with provenance and hashes. Actual Rollup module inputs are cross-checked against this inventory. Packages explicitly restricted to unbundled use fail packaging if they contribute browser code. Prebundled icon attribution is retained as well. See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

Local build metadata schema 2 binds both output hashes to all files under `src/`, `package.json`, `package-lock.json` and `vite.config.js`, including the production build command/mode. The release code independently enumerates and hashes these inputs and rejects stale, incomplete or unexpected evidence. Source changes during compilation also fail the build.

The local source gate performs locked dependency installation, JS/client tests, a complete audit, Python tests, **two byte-identical frontend compilations** and **two byte-identical archive constructions**. The fixed runtime payload includes `BUILD.json`, source-commit identity and complete notices. Clean HEAD/worktree, file inventories, path safety, symlink ancestors, limits and hashes are checked before output. These checks require a trusted build host; they are not a signature against an attacker controlling the build tools and metadata together.

Generated assets and verification archives remain generated output. The repository contains the full source, lockfile, original license material, build/packaging code and tests needed to reproduce them. The candidate is unsigned and carries `production_approved=false`.

## 5. Local quality assurance and reproducibility

GitHub Actions quota is exhausted. The existing workflow now has **only `workflow_dispatch`**, with no push or pull-request trigger. It was not dispatched. Current results are local and must not be represented as hosted CI success.

The test layers are deliberately distinguished:

- Unit tests exercise parser/crypto, transport, session/create rules, presenter and controller failures with controlled dependencies and clocks.
- Pinned-client tests run the actual Passwords client and libsodium against synthetic challenges, including CSE and secondary-factor handling.
- Compiled-browser tests use the actual production Vue bundle, client and browser WebCrypto with synthetic HTTPS API/shell responses. They cover keyboard, failure, timing, theming and reflow cases.
- Real integration runs against a disposable installed Nextcloud/Passwords server with real routing, cookies, CSRF, CSP, database and API behavior. It covers both ordinary and client-side-encrypted vaults.
- Python tests and clean-source gates verify build/package/install boundaries. The migration does not run a production installer to manufacture an acceptance result.

Exact totals, versions, asset hashes and remaining test boundaries are recorded in [VALIDATION_VUE_1.1.0.md](VALIDATION_VUE_1.1.0.md). [DEVELOPMENT.md](DEVELOPMENT.md) contains commands; `tests/integration/` documents the real-server runner and its disposable-environment requirements.

## 6. Release boundaries and follow-up

The complete migration is source-deliverable through a feature branch and pull request. The published v1.0.0 tag and release assets remain untouched. The missing `<bugs>` URL from [PR #5](https://github.com/RamonP12/nextcloud-passwords-otp-extension/pull/5) is incorporated narrowly into 1.1.0 metadata; the separate 1.0.1 branch is not merged. [PR #9](https://github.com/RamonP12/nextcloud-passwords-otp-extension/pull/9) remains the separate App Store/signing effort.

The real disposable fixture uses SQLite and the exact Nextcloud/Passwords/PHP versions in the validation record. It is not an AIO/PostgreSQL or production upgrade acceptance. The existing AIO tool intentionally accepts only a first install and refuses an existing app; a supported in-place AIO upgrade procedure is still a separate deployment task.

Automated WCAG rule checks, keyboard coverage and reflow tests provide specific evidence. They do not certify all accessibility requirements, native browser zoom, screen-reader behavior or every mobile browser. Live Passwords app-level second-factor testing is limited by the pinned upstream feature manifest; the real-client synthetic challenge tests remain explicit evidence for that path.

No live credentials, user vault data, production settings, GitHub branch protections, published tags or release assets are modified by this migration.
