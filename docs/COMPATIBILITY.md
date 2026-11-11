# Compatibility and supported scope

## Validated environment

| Component | Verified | Boundary |
| --- | --- | --- |
| Nextcloud | 35.0.2 / internal 35.0.2.2 | appinfo currently restricts the major version to 35 |
| Nextcloud Passwords | 2026.11.20 | Depends on internal upstream PHP classes and API behavior |
| PHP | 8.4.27 live AIO; PHP 8.5.12 synthetic security contracts | appinfo declares 8.3–8.5 |
| Databases | PostgreSQL on a small AIO pilot; MariaDB 11.8 local fixture | Not a broad matrix |
| Browser | Real desktop pilot; synthetic Chromium tests | Other browsers/mobile not exhaustively tested |
| Container | Official AIO image, persistent app volume | Installer rejects other images/setup |

**No guarantee is made for newer Nextcloud or Passwords versions.** Updating the original Passwords app may change internal ApiTokenHelper / EnvironmentService interfaces. Test a new combination before upgrading.

## Product boundaries

- Own and shared, valid **TOTP** fields; **no HOTP**.
- Create new Passwords entries; existing entries edited and shared in the original Passwords app.
- Local WebCrypto code calculation; CSE and Passwords API authentication needed to read vault data.
- Manual AIO **first install only**. An existing OTP deployment cannot be overwritten by aio_install.py.
- Unofficial, unsigned source distribution; no App Store support or automatic update channel.

**Automated v1.0.0 release checks passed; a real first-install test of the v1.0.0 package is still pending.** The release ZIP, hashes, source commit and third-party notices have been independently checked; this is not an end-to-end AIO acceptance test. Earlier internal-version observations are separated in [Validation](VALIDATION.md).
