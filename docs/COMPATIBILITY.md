# Compatibility and supported scope

**Release distinction (2026-11-11):** The **published v1.0.0** ZIP passed 49/49 local acceptance checks. The **v1.0.1 metadata-only candidate** retains the identical audited OTP runtime and Nextcloud/Passwords compatibility declaration but requires its **own version-bound package tests and live browser installation acceptance**. The target AIO/PostgreSQL first install and production sign-off remain open; do not generalize the 1.0.0 observations to a new binary.

## Validated environment

| Component | Verified | Boundary |
| --- | --- | --- |
| Nextcloud | 35.0.2 / internal 35.0.2.2 | appinfo currently restricts the major version to 35 |
| Nextcloud Passwords | 2026.11.20 | Depends on internal upstream PHP classes and API behavior |
| PHP | 8.4.27 live AIO; PHP 8.5.12 synthetic security contracts | appinfo declares 8.3–8.5 |
| Databases | MariaDB in the verified published-ZIP local test; PostgreSQL only in an earlier internal AIO pilot | Published v1.0.0 ZIP **not** yet accepted on AIO/PostgreSQL |
| Browser | Real localhost desktop functional tests in Chrome/Firefox; earlier synthetic Chromium tests | Other browsers/mobile not exhaustively tested |
| Container | Official AIO image, persistent app volume | Installer rejects other images/setup |

**No guarantee is made for newer Nextcloud or Passwords versions.** Updating the original Passwords app may change internal ApiTokenHelper / EnvironmentService interfaces. Test a new combination before upgrading.

## Product boundaries

- Own and shared, valid **TOTP** fields; **no HOTP**.
- Create new Passwords entries; existing entries edited and shared in the original Passwords app.
- Local WebCrypto code calculation; CSE and Passwords API authentication needed to read vault data.
- Manual AIO **first install only**. An existing OTP deployment cannot be overwritten by aio_install.py.
- Unofficial, unsigned source distribution; no App Store support or automatic update channel.

**2026-11-11: the exact public v1.0.0 ZIP passed first app installation into an existing disposable localhost Nextcloud/MariaDB fixture: 10/10 blocks and 49/49 checks, including an out-of-group negative test, CSE and release-file integrity.** This is **not** an AIO/PostgreSQL first-install or general production acceptance. The release ZIP, hashes, source commit and third-party notices remain unchanged. See [local acceptance](LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md), [release integrity](RELEASE_INTEGRITY_v1.0.0.md) and [validation](VALIDATION.md).
