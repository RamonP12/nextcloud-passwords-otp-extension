# Manual AIO first-install – Passwort OTP Code Generator v1.0.0

**Scope:** a fresh installation of `passwords_otp` on Nextcloud AIO with **Nextcloud 35.0.2**, official **Passwords 2026.11.20**, PostgreSQL, PHP 8.3–8.5, persistent `custom_apps` storage and a valid restricted user group.

**Automated v1.0.0 release checks passed; a real first-install test of the v1.0.0 package is still pending.** No general production or App Store approval is claimed. The package is unsigned; `BUILD.json` intentionally contains `production_approved=false`.

**No in-place upgrades.** The AIO installer refuses an existing `passwords_otp` app. The original Passwords app is not changed. The legacy flag `--accept-unapproved-rc` remains the explicit acknowledgement required by the v1.0.0 installer; it does not denote an approved release.

## 1. Verify backup, release files and environment

Verify a restorable AIO/Borg backup, including PostgreSQL and the application volume, and retain a working restoration procedure.

Use the **immutable [v1.0.0 tag](https://github.com/RamonP12/nextcloud-passwords-otp-extension/tree/v1.0.0)** (commit `56d6de06e4825c9bd03b4b07dec5825d64228390`) to obtain the two scripts `scripts/aio_install.py` and `scripts/release.py`. Obtain the matching ZIP from the [v1.0.0 release assets](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.0.0). Follow [Installation](INSTALLATION.md) for exact download, hash and same-tag instructions.

Transfer **`passwords_otp-1.0.0.zip`, `aio_install.py` and `release.py`** to a private directory on the AIO host and restrict access (`chmod 600` on all three files). Never mix installer scripts from `main` with the `v1.0.0` archive.

On the **AIO host**, in that private directory:

```sh
sha256sum passwords_otp-1.0.0.zip
# The following SHA must match the independently verified release asset:
# ffc002d7c41485cac4a4b7eb27659fd5d5dbbd4bd7fd40d78e3ea91373a12256

OTP_SHA="$(sha256sum passwords_otp-1.0.0.zip | cut -d' ' -f1)"
test "$OTP_SHA" = 'ffc002d7c41485cac4a4b7eb27659fd5d5dbbd4bd7fd40d78e3ea91373a12256'

sudo python3 aio_install.py --inspect
```

Expected: `AIO_INSPECT_PASS`. Stop if the environment, image, Nextcloud/Passwords/PHP versions, PostgreSQL or volume do not match the supported combination. `SHA256_FROM_THIS_PACKAGE` in older examples means the **actual verified ZIP hash**, never a hash copied from another build.

## 2. Check the group and perform preflight

Replace `otp-pilot` below with the **exact existing Nextcloud group ID**. This does not create a group.

```sh
sudo docker exec -u www-data nextcloud-aio-nextcloud \
  php /var/www/html/occ group:info 'otp-pilot' --output=json

sudo python3 aio_install.py --preflight \
  --package ./passwords_otp-1.0.0.zip \
  --sha256 "$OTP_SHA" \
  --group 'otp-pilot'
```

Expected: `AIO_PREFLIGHT_PASS` and scope `otp-pilot`. Preflight does not change Nextcloud app data but writes an installer receipt under `/var/lib/passwords-otp-aio-installer/`. A missing group causes a **STOP**, never a global-access fallback.

## 3. Explicit first-time install

Only after reading the receipt, verifying the backup and acknowledging the [WebUI token residual risk](SECURITY_REVIEW.md):

```sh
sudo python3 aio_install.py --install \
  --package ./passwords_otp-1.0.0.zip \
  --sha256 "$OTP_SHA" \
  --group 'otp-pilot' \
  --confirm-production \
  --ack-aio-backup \
  --accept-unapproved-rc \
  --accept-browser-token-risk
```

Expected: `AIO_INSTALL_PASS: 1.0.0`. The installer stages only `passwords_otp` in the persistent `custom_apps` volume, checks file hashes, enables the app through `occ` and verifies group scope. No SQL patch or container restart is intended.

If it prints `STOP`, **do not retry blindly**; inspect the transaction journal and effective app registration first.

## 4. Independent verification and browser acceptance

```sh
sudo python3 aio_install.py --verify \
  --package ./passwords_otp-1.0.0.zip \
  --sha256 "$OTP_SHA"

sudo docker exec -u www-data nextcloud-aio-nextcloud \
  php /var/www/html/occ config:app:get passwords_otp enabled
```

Expected: `AIO_VERIFY_PASS` and a group-scoped JSON value such as `["otp-pilot"]`. The value `yes` indicates global enablement and is unacceptable unless `--all-users` was explicitly requested and approved.

Use two distinct real browser sessions: one authorized member of `otp-pilot`, one user **outside** the group. With *synthetic* entries check TOTP display and copy, shared entries, CSE challenge, new record creation, logout and expiration. Do not paste real secrets or full request bodies in public Issues.

## 5. Rollback / emergency disable

Retain the exact installed ZIP, corresponding source commit, checksum, scripts and state receipts. Normal rollback refuses identity or file drift:

```sh
sudo python3 aio_install.py --rollback \
  --package ./passwords_otp-1.0.0.zip \
  --sha256 "$OTP_SHA" \
  --confirm-production \
  --ack-aio-backup
```

After an AIO update, `--allow-aio-update-for-rollback` permits only an *explicitly confirmed* emergency disable of the exact app installation recorded by this tool. It verifies receipt, unchanged app files, registration and persistent volume, **but it does not restore the database**. Use the independent AIO backup if identity or state is uncertain.

**Earlier internal versions:** `0.7.3` was never a public release. These commands apply only to an original `v1.0.0` installation recorded by this installer; do not use them to alter an existing internal pilot installation.
