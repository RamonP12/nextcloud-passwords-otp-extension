# Version 1.1.2 verification

Version 1.1.2 adds the enforced Passwords prerequisite and deterministic tar.gz
distribution to the published 1.1.1 Nextcloud Vue edition. The UI wording,
TOTP calculation, encrypted vault handling and create-only product scope remain
unchanged. This record covers the new source and does not reuse old test totals
as proof of the changed backend behavior.

## Results on 2026-11-19

The clean implementation commit **`36c78d2721432644651f3deae8de3708ea0191ac`**
passed the complete local build gate. The independent PHP/lifecycle review also
passed. The following evidence is tied to the exact tested source/asset hashes:

| Check | Result | Evidence boundary |
| --- | --- | --- |
| JavaScript regression | **237/237 passed** | Unit and source-contract tests |
| Actual pinned Passwords client/libsodium | **17/17 passed** | Synthetic API responses |
| Python release/install/rollback/TAR/signing | **102/102 passed** | Includes 19 TAR/cryptographic/adversarial cases; no production certificate |
| PHP security and dependency checks | **67 + 110 assertions passed** | PHP 8.4.27, standalone contract doubles |
| PHP syntax | **13/13 files passed** | Runtime, contract suites and core harness |
| Nextcloud 35.0.2 core components | **24/24 cases passed** | 34 verified upstream source files; DI/database/registration services replaced |
| Compiled Firefox browser suite | **30/30 cases passed** | Actual Vue assets in a synthetic shell/API; matching clean-build asset hashes |
| Nextcloud 35 metadata XSD | **Passed** | Official pinned schema, including job/repair element ordering |
| npm audit at build time | **0 reported vulnerabilities** | Exact locked dependency graph; not a security certification |
| Two frontend builds | **Byte-identical** | JS and CSS |
| Repeated ZIP and TAR packaging | **Byte-identical** | Same commit, exact same runtime files; one TAR root |

The clean build used Node.js 24.22.3, npm 11.9.0 and Python 3.12.14;
browser tooling was Playwright 1.62.0. Chromium was not rerun: the previous
attempt in this workspace was blocked by a socket permission error before app
startup. No current Chromium pass is asserted. The previously reported real
localhost checks remain separate from the Firefox synthetic suite.

The source comparison confirms that frontend modules other than the two version
marker files are unchanged from 1.1.1. No npm dependency version was changed.
The release gate also verifies the source/module inventory and original bundled
licence notices. Existing Vite warnings about the app-root output directory and
large single bundle remain; the output allowlist, source-freshness gate and
deterministic build checks pass.

See [additional checks](validation/1.1.2/additional-checks.json),
[build receipt](validation/1.1.2/build-pass.json),
[PHP checks](validation/1.1.2/php-contracts.json),
[core component cases](validation/1.1.2/nextcloud-core-components.json),
[browser cases](validation/1.1.2/browser-firefox.json) and
[bundle provenance](validation/1.1.2/bundle-modules.json).

The local and release ZIP packages have different whole-archive SHA256 digests,
although a later operator comparison found **all 18 runtime files and the
BUILD.json manifest identical**. The cause is undetermined; the repeatability
claims above apply to reruns within the recorded build environment, not
cross-environment compressed-byte identity. Details and exact digests are in
[the post-release localhost report](LOCAL_ACCEPTANCE_v1.1.2_2026-11-19.md).

The final version-bound results and reviewed source hashes are recorded in
`docs/validation/1.1.2/`. The GitHub Release's `BUILD.json` binds its archives to
the exact published source commit; final archive checksums are attached to that
release. Build provenance changes when a documentation/evidence commit changes
the source commit, even if compiled runtime bytes are unchanged.

## Evidence scope

All verification is local. GitHub Actions is unavailable and has not been
dispatched. The retained workflow has only an explicit manual trigger.

- JavaScript tests cover the existing parser/crypto, transport, session,
  creation and presentation contracts.
- Pinned Passwords client/libsodium tests use the actual dependencies with
  synthetic upstream responses.
- Python tests cover packages, licenses, source provenance, deployment gates,
  rollback and adversarial TAR/signature cases. Cryptographic tests use
  ephemeral synthetic certificates, never a trusted production app certificate.
- PHP contracts exercise dependency state, per-user access, event handling,
  job cleanup, migration behavior and the original controller/session safeguards.
- The Nextcloud core-component suite loads unchanged upstream core classes
  pinned by SHA256, using isolated framework/database services. It exercises
  actual installer, migration, app-manager, repair, event and CLI code. It is
  **not** a running Nextcloud/Passwords instance.
- The compiled browser suite loads the production Vue assets in a synthetic
  HTTPS shell/API. It is not live-server routing or authenticated Passwords
  acceptance.
- Metadata is checked against Nextcloud 35's official XSD. Repeated compiled
  builds and both archive formats were byte-identical in the recorded build environment. Cross-environment archive byte identity is not established.

## Installed-server and publication boundaries

The maintainer accepted five functional checks on candidate 1.1.0 in the existing
Nextcloud 35.0.2.2 / Passwords 2026.11.20 / PHP 8.5 / MariaDB localhost fixture.
Those checks are recorded in [1.1.1 verification](VALIDATION_VUE_1.1.1.md).
**Post-release update:** The maintainer subsequently upgraded the existing localhost
fixture from OTP 1.1.0 to **1.1.2** using the version-matched installer. The
backup, installation, HTTP assets and final verification passed. Disabling
Passwords synchronously disabled OTP; attempted OTP enablement was denied with
exit code 1; restoring Passwords did not automatically enable OTP; manual OTP
activation succeeded. Existing accounts, changing TOTP codes and creation of a
test entry were also confirmed. These observations are documented separately
in [1.1.2 localhost acceptance](LOCAL_ACCEPTANCE_v1.1.2_2026-11-19.md). The
maintainer's **live** lifecycle acceptance tests were not part of the original
release build; automated PHP/core-component lifecycle tests were. The new
live observations do not retroactively alter the signed/unsigned release
evidence. Fresh installation, removal with retained data, eventless loss,
group isolation and other versions remain untested on this fixture; see
[Dependency lifecycle](DEPENDENCY_LIFECYCLE.md).

The release is a **manual, unsigned GitHub distribution**. Its tar.gz has the
required single `passwords_otp/` root and compiled runtime payload. Nextcloud
code signing, certificate trust, the detached archive signature, App Store
registration/publication and review of the upstream private API coupling remain
separate requirements. No signing credential was supplied for this release.
`production_approved=false` remains unchanged. No production AIO/PostgreSQL
upgrade approval is inferred from these tests.
