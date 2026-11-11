# v1.0.0 – Initial public-source baseline

> **Historical notes preserved as a publication-time snapshot:** The release body below originally said a real v1.0.0 first-install was still pending. On 2026-11-11, **after publication**, the exact ZIP passed a **local Docker Compose/MariaDB app-installation and 49/49 manual checks**. The **AIO/PostgreSQL first-install remains pending**. Current evidence: [local acceptance](LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md), [validation](VALIDATION.md), [release integrity](RELEASE_INTEGRITY_v1.0.0.md). This addition to `main` documentation does **not** modify the published release description, tag or binary assets.

**Passwort OTP Code Generator** is an independent, unofficial, desktop-oriented companion for [Nextcloud Passwords](https://apps.nextcloud.com/apps/passwords). It displays and copies TOTP codes from personal and shared Passwords records and supports creating new Passwords records with compatible OTP custom fields. It does not modify the original Passwords app.

## Compatibility and verification

- **Tested API combination:** Nextcloud **35.0.2** (internal build 35.0.2.2), Passwords **2026.11.20**, PHP 8.4 pilot / PHP 8.5 automated contracts. Wider environments are **not** validated.
- **Test results:** JavaScript 179/179, pinned upstream client 17/17, Python 66/66; npm audit reported 0 vulnerabilities at build time.
- **Source tag:** [`v1.0.0`](https://github.com/RamonP12/nextcloud-passwords-otp-extension/tree/v1.0.0) at commit `56d6de06e4825c9bd03b4b07dec5825d64228390`.
- **ZIP SHA256:** `ffc002d7c41485cac4a4b7eb27659fd5d5dbbd4bd7fd40d78e3ea91373a12256`.
- **Signing:** This is an **unsigned** source distribution, **not published in the Nextcloud App Store**.
- **Approval:** `production_approved=false`. **Automated v1.0.0 release checks passed; a real first-install test of the v1.0.0 package is still pending.**

Download `passwords_otp-1.0.0.zip`, `passwords_otp-1.0.0.zip.sha256` and `BUILD.json` from the assets attached below. Verify the archive **before installation**:

```sh
sha256sum -c passwords_otp-1.0.0.zip.sha256
printf '%s  %s\n' \
  'ffc002d7c41485cac4a4b7eb27659fd5d5dbbd4bd7fd40d78e3ea91373a12256' \
  'passwords_otp-1.0.0.zip' | sha256sum -c -
```

Both checks must print `OK`.

## Known limitations and security boundaries

- **[Issue #1 – upstream Passwords WebUI token privilege](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1):** The token can authorize more operations than the narrow OTP viewer/creator exposes; a browser-side allowlist is not a server-enforced privilege boundary.
- **No HOTP**; the UI does not edit or delete existing records.
- Supported scope is **manual, group-restricted AIO first-time installation**. There is no tested in-place upgrade from unpublished earlier versions.
- The UI is primarily German; browser extensions and clipboard access remain security considerations.
- No general production certification, support warranty or App Store approval is implied.

Review [full validation evidence](https://github.com/RamonP12/nextcloud-passwords-otp-extension/blob/main/docs/VALIDATION.md), [installation guide](https://github.com/RamonP12/nextcloud-passwords-otp-extension/blob/main/docs/INSTALLATION.md) and [security policy](https://github.com/RamonP12/nextcloud-passwords-otp-extension/blob/main/.github/SECURITY.md) before installing. Never use `main` to reproduce the tagged v1.0.0 ZIP.
