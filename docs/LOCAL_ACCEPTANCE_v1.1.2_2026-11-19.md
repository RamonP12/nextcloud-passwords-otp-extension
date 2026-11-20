# Maintainer-reported localhost acceptance: OTP 1.1.2 (2026-11-19)

## Outcome and evidence scope

**PASS for the observed local upgrade, positive Passwords lifecycle and basic OTP functionality on this one fixture.** These results were supplied by the maintainer as console output and an administrator-apps screenshot. They are not newly generated remote logs or independently rerun checks. This file was added after the immutable GitHub v1.1.2 release; it does not alter the tagged source, published archives or historical validation receipts.

- **Source and release:** v1.1.2, commit **25006dd47b3a6f40ff409ffb1096ed78ea3bdfa5**.
- **Environment:** existing localhost-only Docker Compose Nextcloud 35.0.2.2 / Passwords 2026.11.20 / PHP 8.5 / MariaDB fixture, upgraded from locally installed OTP 1.1.0. MariaDB 11.8 was reported in earlier fixture records but was not independently remeasured during this upgrade.
- **Not the production AIO/PostgreSQL server.** No signing certificate was used.

## Package and deployment checks

| Step | Maintainer-observed result |
| --- | --- |
| Clean tagged source | v1.1.2 at exact release commit; no tracked/untracked changes |
| Local build | BUILD_PASS; locally produced ZIP SHA256 **ae940a851aeed72c0e0029231d30389d63d8ad136152efbbe0c3b0d47dde89f7** |
| Local preflight | Browser suite 30 cases passed; HTTP_ASSETS_PASS app-110; LOCALHOST_PREFLIGHT_PASS |
| Downloaded release ZIP | GitHub SHA256 **4e5781c4b5679c08e127bdf87f3496c0d9f1d028c1674ce1d1f33cb5a2f7ed05**, matching published release metadata |
| Archive contents comparison | **18 files compared, 0 different; matching BUILD.json manifests; PAKETVERGLEICH_PASS** |
| Upgrade | Backup and transaction journal produced; HTTP_ASSETS_PASS app-112; INSTALL_PASS version=1.1.2; installer exit code 0 |
| Post-install verification | HTTP_ASSETS_PASS app-112; LOCALHOST_VERIFY_PASS; exit code 0 |
| Administrator Apps page | Passwords 2026.11.20 and Passwort OTP Code Generator 1.1.2 displayed |

The backup location and transaction identifier remain private to the operator.
The deployment tool's automatic rollback remains available but **no real rollback
was exercised in this acceptance**.

### Archive byte reproducibility

The locally built and officially published ZIPs report **different SHA256 values**
even though all 18 extracted files and their manifests matched. The build receipt
also reported a local TAR hash differing from the published release TAR.
The original comparison established identical extracted ZIP content. A later
controlled run with this release reproduced different compressed bytes by
swapping classic zlib for zlib-ng while preserving the uncompressed files.
The original local archives were unavailable to that follow-up.
[Controlled comparison and verification commands](DEVELOPMENT.md#compare-a-rebuild-with-a-release)

## Actual Passwords dependency lifecycle

The maintainer's observed console results were:

| Sequence | Result |
| --- | --- |
| Start: Passwords 2026.11.20 enabled; OTP 1.1.2 enabled | PASS |
| Disable Passwords using Nextcloud occ | Passwords disabled and OTP automatically disabled — PASS |
| Attempt to enable OTP while Passwords is disabled | Clear prerequisite error; exit code 1; OTP remains disabled — PASS |
| Re-enable Passwords | Passwords enabled; OTP correctly remains disabled — PASS |
| Explicitly re-enable OTP | OTP enabled; final state Passwords=yes, OTP=yes — PASS |

The console reported **LIFECYCLE_PASS**. This validates the supported
**normal disable / invalid enable / explicit recovery** path on the installed
Nextcloud/MariaDB fixture; it is not evidence of every path listed in the
component-only lifecycle suite.

## Actual OTP operation after upgrade

After restoring both apps to enabled state, the maintainer confirmed that
existing OTP entries are displayed, TOTP codes continue changing correctly and
creation of a new synthetic OTP record still works as expected. The Nextcloud
administrator Apps page displayed the two expected versions. This is
maintainer-reported manual testing, without a separately preserved new
independent RFC6238 vector trace. The original five independent functional
checks were completed on the earlier Vue 1.1.0 candidate and retain their own
[historical record](VALIDATION_VUE_1.1.1.md).

## Remaining test gaps

- Fresh installation without Passwords, including absence of files, installed
  registration, and incompatible version: use a separate disposable fixture.
- Full Passwords removal and removal with preserved data, missed events, file
  deletion, timing of scheduled fallback.
- Per-user Passwords group exclusion while another user remains authorized.
- Different Passwords versions, PHP and database combinations, production
  AIO/PostgreSQL behavior, actual App Store signature verification.
- Full browser/accessibility matrix; no new current Chromium pass is claimed.

**Scope conclusion:** OTP 1.1.2 is locally accepted for the tested upgrade,
normal disable/reenable, and core OTP flows in this fixture only.
The release remains unsigned and **production_approved=false**.

## Branding backlog (no implementation)

The observed administrator listing still uses **Passwort OTP Code Generator**.
The proposed rename to **Passwords OTP Generator** and a shield with a diagonal
negative-space key are documented in [issue #12](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/12).
No 1.1.2 app metadata, SVG, assets or existing tag/release were changed.
