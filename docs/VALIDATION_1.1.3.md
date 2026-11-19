# Version 1.1.3 release and verification

GitHub published [v1.1.3](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.3) as the latest release on 2026-11-19. The tag points to the [PR #15 squash commit](https://github.com/RamonP12/nextcloud-passwords-otp-extension/commit/ae1096099521dcf9bf7bc6f5e5011f88bced5916) and GitHub reports the release as immutable. The release adds the **Passwords OTP Generator** name, shield icon and direct code copying. The internal app ID is `passwords_otp`.

## Published packages

Use the compiled ZIP for the version-matched installer tooling and the compiled TAR.GZ for manual distribution. Each archive contains the same 18 files inside one `passwords_otp/` root. The attached `BUILD.json` identifies app version 1.1.3, records the source commit and lists the runtime file hashes. All five release attachments were downloaded after publication and matched the build outputs byte for byte.

| Archive | SHA-256 |
| --- | --- |
| `passwords_otp-1.1.3.zip` | `92021a9bc69d3a12378fc33de483fdb0806cacc240269a08b350234846a469dd` |
| `passwords_otp-1.1.3.tar.gz` | `2019ff98d6decadc7fbbd14f3a486a9b3a7898a407fa5bfe3cd82b91f94197cc` |

The GitHub artifacts are unsigned Nextcloud packages with `production_approved=false`. Archive checksums verify byte identity. Independent cryptographic verification of the GitHub release attestation is tracked in [#3](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/3). Nextcloud certificate signing and App Store submission are tracked in [#14](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/14). Cross-environment archive reproducibility is tracked in [#16](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/16).

## Verification by environment

| Environment | Observed result |
| --- | --- |
| Build from the published merge commit | 238 JavaScript tests, 17 upstream-client tests and 102 Python tests passed. The build gate completed both bundle builds and the deterministic packaging checks. npm audit reported zero vulnerabilities. |
| Compiled browser suites | Chromium and Firefox each passed 32 cases with synthetic API, shell and clipboard fixtures. Cases cover direct code click, keyboard activation, leading zeroes, clipboard errors, near-expiry denial and the icon at 16, 24 and 32 pixels. Bundle hashes matched the merge-commit build. |
| PHP and pinned Nextcloud core components | On PHP 8.4.27, the security and dependency suites passed 67 and 110 assertions, 13 PHP files passed syntax checks, the app metadata validated against the Nextcloud 35.0.2 XSD, and 24 lifecycle component cases passed with service doubles. |
| Maintainer preflight | Nextcloud 35.0.2 (internal 35.0.2.2), PHP 8.5.12, MariaDB and Passwords 2026.11.20. PHP contracts and all 32 compiled browser cases passed. The preflight verified the installed 1.1.2 assets before the upgrade. |
| Maintainer upgrade and manual acceptance | The 1.1.2 → 1.1.3 transaction created and verified a backup. Installed files and served `app-113` assets passed post-install verification. The maintainer confirmed unlocking the vault, finding existing OTP entries, copying codes and creating a test entry. The screenshot showed the new name and shield icon. |
| Separate real-server fixture | On Nextcloud 35.0.2 / PHP 8.4.27 / SQLite with Passwords 2026.11.20, the upgrade retained an existing synthetic entry. The app name in the Apps list and browser title, served SVG, both copy controls and creation passed. A manual rollback to 1.1.2 retained both synthetic entries. |

The maintainer installed a package built from the [reviewed PR head](https://github.com/RamonP12/nextcloud-passwords-otp-extension/commit/9120b4189a16808cbb0961fa58bf343688471c6b). The published archive was built after the squash merge. The Git trees are identical. Each build manifest records its own commit, so use the published release checksums when verifying downloads.

The installed-server evidence covers those two fixtures. Component tests cover additional dependency cases with service doubles. The [dependency lifecycle](DEPENDENCY_LIFECYCLE.md) lists the cases still requiring live checks. First installation on AIO/PostgreSQL, a production AIO upgrade and signed App Store installation still require separate verification.

See [installation and version selection](INSTALLATION.md), the [release page](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.3) and the [PR verification record](https://github.com/RamonP12/nextcloud-passwords-otp-extension/pull/15).
