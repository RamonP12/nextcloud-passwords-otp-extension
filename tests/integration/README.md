# Real Nextcloud integration acceptance

`nextcloud.py` runs against an actual disposable Nextcloud installation, with the
released Passwords app and this app's compiled Vue assets. It supplements
`tests/browser/desktop.py` and `tests/browser/lifecycle.py`, whose server responses
and Nextcloud shell are synthetic.

The integration runner does not replace HTTP responses, the upstream client,
libsodium, browser WebCrypto, the system clock or the clipboard API. Credentials
come exclusively from environment variables. Reports contain version labels,
asset hashes, assertion results and accessibility findings; they do not contain
request bodies, tokens, passwords, account cookies or browser storage snapshots.

## Safety and fixture requirements

The runner deliberately requires both `OTP_E2E_DISPOSABLE=1` and a loopback HTTPS
URL. It creates synthetic Passwords records, changes the normal test user's
light/dark preference, clears browser cookies and tests refused authentication
requests. With administrator credentials, it temporarily changes the server's
primary brand color and restores the preceding color in `finally`.

Use dedicated test accounts and destroy the fixture afterwards. Do not run this
against production data. The created synthetic records remain available for
inspection; cleanup belongs to destruction of the disposable installation.
The script refuses arbitrary remote production URLs. A local tunnel alone does
not make a production server an appropriate fixture.

Provide these accounts:

| Account | Requirements |
| --- | --- |
| Normal test user | German Nextcloud language; Passwords available; no Passwords master challenge; member of the group permitted to use `passwords_otp`. |
| Sharing owner / outsider | Passwords available; outside the group permitted to use `passwords_otp`; has shared one TOTP record read-only with the normal user. |
| CSE test user | German Nextcloud language; Passwords master challenge and CSE enabled through the real Passwords app/client; member of the permitted group. |
| Optional administrator | Dedicated fixture administrator for real server brand-color acceptance. |

Disable or complete Nextcloud's initial first-run overlay in the fixture before
running the test; it otherwise intercepts app controls. Browser requests to other
origins are blocked by the runner. This keeps the disposable test self-contained;
external avatars, recommendations or other nonessential integrations are not
part of the acceptance scope.

The shared test record must have `cseType: "none"`, a nonempty `share` property
and `editable: false` in the real recipient's Passwords API response. Its OTP
field must contain the public RFC 6238 SHA-1 test secret:

```json
[
  {
    "label": "client.ios.otp",
    "type": "data",
    "value": "{\"type\":\"totp\",\"secret\":\"GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ\"}"
  }
]
```

Use 6 digits and a 30-second period. Give it a unique, synthetic label and pass
that label in `OTP_E2E_SHARED_LABEL`. Creating the share through the original
Passwords UI or API, and running the original sharing background job, ensures
this is a genuine incoming share. The test checks the server's incoming-share
and read-only flags before comparing its displayed OTP with an independent HMAC
calculation. It observes that no `password/update`, `password/delete` or
`password/restore` call is issued by the extension.

## Installation and execution

Build the release assets first, install the app in the fixture and enable it for
the test group. Follow the repository's normal Nextcloud installation and PHP
requirements. The runner accepts a webroot prefix in `OTP_E2E_BASE_URL`.

Install the browser harness in a local Python environment:

```sh
python3 -m pip install playwright==1.62.0
python3 -m playwright install chromium firefox
npm ci
npm run build
```

Supply these variables through a private shell environment or an untracked
fixture configuration. Do not commit actual values:

| Variable | Meaning |
| --- | --- |
| `OTP_E2E_DISPOSABLE=1` | Explicitly identifies the destructive disposable fixture. |
| `OTP_E2E_BASE_URL` | Loopback HTTPS origin, optionally including a webroot prefix, e.g. `https://127.0.0.1:8443`. |
| `OTP_E2E_USER`, `OTP_E2E_PASSWORD` | Normal test user's Nextcloud credentials. |
| `OTP_E2E_SHARED_LABEL` | Unique label of the incoming read-only synthetic TOTP share. |
| `OTP_E2E_OUTSIDER_USER`, `OTP_E2E_OUTSIDER_PASSWORD` | User outside the app's enabled group. |
| `OTP_E2E_CSE_USER`, `OTP_E2E_CSE_PASSWORD`, `OTP_E2E_CSE_MASTER` | CSE account's Nextcloud login and separate Passwords master password. |
| `OTP_E2E_ADMIN_USER`, `OTP_E2E_ADMIN_PASSWORD` | Optional fixture administrator for brand testing. |
| `OTP_E2E_IGNORE_HTTPS_ERRORS=1` | Accept a local fixture's self-signed certificate. Omit when the certificate is trusted. |
| `OTP_E2E_NEXTCLOUD_VERSION`, `OTP_E2E_PASSWORDS_VERSION`, `OTP_E2E_DATABASE` | Fixture provenance labels recorded in the report; verify from the actual installation. |
| `CHROME_BIN` | Optional installed Chromium/headless-shell executable; otherwise Playwright's Chromium is used. |
| `PLAYWRIGHT_BROWSERS_PATH` | Optional location of Playwright-managed browser binaries. |

Run from the repository root:

```sh
python3 tests/integration/nextcloud.py --browser chromium
python3 tests/integration/nextcloud.py --browser firefox --core-only
```

Omit `--core-only` to run the theme, accessibility and viewport matrix in Firefox
as well. Missing optional accounts are explicitly marked `SKIP`, not `PASS`.
A passing run with skipped shared or CSE checks does not establish that coverage.
The runner exits nonzero on assertion failure and writes a report even on failure.

Artifacts default to `.build/real-integration/`:

- `report-chromium.json` / `report-firefox.json`: sanitized scope, exact browser
  version, supplied server provenance, asset SHA-256 values and results.
- Screenshots: actual Nextcloud shell and Vue app, using synthetic accounts only.

Do not publish screenshots from any fixture containing real accounts or data.
Review evidence before copying selected artifacts into release documentation.

## Assertions and their practical limits

The runner checks the actual PHP template and `type="module"` loader, `.mjs` MIME
type and exact loaded bundle hash, no-store/referrer headers, deployed CSP,
rejected missing-CSRF and mismatched-session requests, and refusal of the user
outside the enabled group. The initial-state element must have been consumed;
the app's verified build marker must be present.

For the normal user, it reads the real incoming share, creates exactly one new
record per explicit save, verifies input Enter does not submit, compares OTPs
against an independent implementation, copies through the real browser API,
checks that native `progress.max` is 30 and `ceil(progress.value)` matches the
textual countdown for the public RFC test record,
filters the list, cycles Tab/Shift+Tab immediately after opening, checks Escape
and focus restoration, and checks that reopening has cleared the secret. Clearing
the Nextcloud browser session and sending a focus event must remove the protected
UI after the real server rejects its session check.

For CSE, a wrong master password must be rejected and cleared. The correct master
password must unlock the actual Passwords challenge/keychain. Creation must send
`CSEv1r1` ciphertext without the plaintext OTP seed or service password; successful
listing and the independently verified OTP then exercise real decryption. This
is substantially different from providing a pre-decrypted fake list to the UI.

The full visual matrix changes the real Nextcloud user theme through its OCS API
and checks list/dialog states at 1440×900, 1024×768, 640×450 and 320×720. It checks
document/content overflow, visibly rendered countdown progress bars, and that
the modal paints above the actual Nextcloud header. The administrator-color scenario changes Nextcloud's actual theming
setting; it does not insert fake CSS variables into the page.

axe-core scans the app and its dedicated dialog portal for WCAG 2 A/AA, 2.1 AA and
2.2 AA tags. Finite entrance transitions are allowed to finish before contrast
measurement. Immediate keyboard containment is tested separately without that
wait. A clean axe result is an automated result, not a declaration of complete
WCAG conformity or a substitute for a manual screen-reader audit.

The report retains axe's `incomplete` items and sanitized manual-review details.
When the modal is open, scanning both app scopes can flag contrast on the covered
background because axe cannot determine colors through the overlay. These
background targets are classified separately; their contrast is checked in the
corresponding closed-dialog list scan. This classification does not suppress an
active-dialog violation or turn an unresolved rule into an automated pass.

Chromium additionally reads back the actual clipboard contents with the browser
permission granted to the test context. Firefox verifies that the real user-click
`clipboard.writeText` call succeeds; its clipboard content is not independently
read by this runner. Browser viewport sizes establish reflow at those sizes;
they do not establish native browser zoom or OS font scaling. No device-scale or
CSS transform is presented as a native zoom test.

An intermediate real Firefox run observed the presenter's safe refusal
`Der Code wird geprüft. Neuen Code verwenden.` between the harness's enabled/
valid-code sample and its click. The presenter intentionally refuses the final
2.5 seconds and changes of validation window. The copy check therefore scrolls
first and waits for a naturally valid, enabled code with more than five seconds
remaining before sampling and clicking. This addresses harness action timing;
the OTP, native progress and clipboard assertions remain intact, and neither the
product's expiry protection nor the real clock is changed.

## Fixture used for the migration assessment

The migration was exercised with the actual Nextcloud **35.0.2.2** code (release
**35.0.2**), Passwords **2026.11.20**, local PHP **8.4.24**, SQLite and a loopback
HTTPS reverse proxy. Both apps were installed unchanged from their official
release archives; `passwords_otp` pointed to the working release assets. This
environment validates actual Nextcloud/session/API/theming integration. It does
not establish AIO, PostgreSQL or production-proxy acceptance.

Primary release sources:

- [Nextcloud 35.0.2 archive](https://download.nextcloud.com/server/releases/nextcloud-35.0.2.tar.bz2)
  and [SHA-256 checksum](https://download.nextcloud.com/server/releases/nextcloud-35.0.2.tar.bz2.sha256).
- [Passwords releases for Nextcloud 35](https://apps.nextcloud.com/apps/passwords/releases?platform=35).
- [Passwords release 2026.11.0](https://github.com/marius-wieschollek/passwords/releases/tag/2026.11.0).
  Its built `appinfo/info.xml` declares **2026.11.20**. The official
  [release archive](https://git.mdns.eu/api/v4/projects/45/packages/generic/passwords/2026.11.0/passwords.tar.gz)
  has SHA-256 `a9ec1a639b89d69c82be23fdbd1c078a54e463df8673490456bd35a968be0820`.

### Live Passwords 2FA limitation

The upstream [Passwords feature manifest](https://raw.githubusercontent.com/wiki/marius-wieschollek/passwords/Users/_features/features-v1.json)
observed during this assessment sets `server["2026.11"]["two-factor-enabled"]`
to `false`. The released `SessionApiController::request` gates its Passwords-level
provider challenge on this flag. No upstream feature flag, challenge controller
or verification implementation was changed to manufacture a live pass.

Consequently, real master-password/CSE acceptance is covered, while real
Passwords-level provider authentication is unavailable in that release
configuration. The separate compiled-bundle browser and client suites test the
provider selector, actual pinned challenge code and retry behavior with synthetic
API responses. Ordinary Nextcloud login 2FA is a separate layer and is not claimed
as tested by this runner.
