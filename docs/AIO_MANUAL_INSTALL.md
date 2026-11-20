# Manual AIO first-install tooling

For an existing 1.1.3 installation, see the separate
[production AIO upgrade record and procedure for 1.1.4](VALIDATION_1.1.4.md).

## Scope for v1.1.3

Use this procedure to evaluate a **fresh installation on a disposable AIO/PostgreSQL
fixture**. The installer expects Nextcloud **35.0.2** by default, PHP 8.3–8.5,
Passwords **2026.11.20** installed and enabled with matching on-disk metadata, a
persistent writable `custom_apps` volume and an existing Nextcloud group.

Use `aio_install.py` and `release.py` from the **v1.1.3** tag with
`passwords_otp-1.1.3.zip`. Keep the source, archive, `BUILD.json`, SHA-256 and
receipts from that version together. Use the corresponding source tag for
earlier archives. The installer consumes the compiled ZIP.

The [v1.1.3 verification record](VALIDATION_1.1.3.md) covers localhost MariaDB,
SQLite, isolated PostgreSQL/Redis fixtures and one manual production AIO
replacement. A live first-install test with this installer on the full
AIO/PostgreSQL stack is open. The package is unsigned and carries
`production_approved=false`. The legacy `--accept-unapproved-rc` flag
acknowledges that package status.

**No production upgrade path is introduced by this tool.** This first-install
tool rejects an existing `passwords_otp` deployment, including the internal
0.7.3 pilot. The [observed manual replacement](VALIDATION_1.1.3.md#maintainer-confirmed-production-aio-replacement-2026-11-19)
has its own acceptance record. The rollback below applies to an installation
recorded by the matching AIO tool.

## 1. Verify backup, release files and environment

Verify a restorable AIO/Borg backup, including PostgreSQL and the application volume, and retain a working restoration procedure.

Use the **pinned [v1.1.3 tag](https://github.com/RamonP12/nextcloud-passwords-otp-extension/tree/v1.1.3)** (commit `ae1096099521dcf9bf7bc6f5e5011f88bced5916`) to obtain the two scripts `scripts/aio_install.py` and `scripts/release.py`. Obtain the matching ZIP from the [v1.1.3 release assets](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.3). Follow [Installation](INSTALLATION.md) for exact download, hash and same-tag instructions.

Transfer **`passwords_otp-1.1.3.zip`, `aio_install.py` and `release.py`** to a private directory on the AIO host and restrict access (`chmod 600` on all three files). Never mix installer scripts from `main` with the `v1.1.3` archive.

On the **AIO host**, in that private directory:

```sh
sha256sum passwords_otp-1.1.3.zip
# SHA-256 of the independently verified release asset
# 92021a9bc69d3a12378fc33de483fdb0806cacc240269a08b350234846a469dd

OTP_SHA="$(sha256sum passwords_otp-1.1.3.zip | cut -d' ' -f1)"
test "$OTP_SHA" = '92021a9bc69d3a12378fc33de483fdb0806cacc240269a08b350234846a469dd' && sudo python3 aio_install.py --inspect
```

Expected: `AIO_INSPECT_PASS`. Stop if the environment, image, Nextcloud/Passwords/PHP versions, PostgreSQL or volume do not match the supported combination. `SHA256_FROM_THIS_PACKAGE` in older examples means the **actual verified ZIP hash**, never a hash copied from another build.

## 2. Check the group and perform preflight

Replace `otp-pilot` below with the **exact existing Nextcloud group ID**. This does not create a group.

```sh
sudo docker exec -u www-data nextcloud-aio-nextcloud \
  php /var/www/html/occ group:info 'otp-pilot' --output=json

sudo python3 aio_install.py --preflight \
  --package ./passwords_otp-1.1.3.zip \
  --sha256 "$OTP_SHA" \
  --group 'otp-pilot'
```

Expected: `AIO_PREFLIGHT_PASS` and scope `otp-pilot`. Preflight does not change Nextcloud app data but writes an installer receipt under `/var/lib/passwords-otp-aio-installer/`. A missing group causes a **STOP**, never a global-access fallback.

## 3. Explicit first-time install

Read the receipt, verify the backup and review the [WebUI token residual risk](SECURITY_REVIEW.md) before installing. The tool requires these acknowledgement flags on the disposable AIO host as well:

```sh
sudo python3 aio_install.py --install \
  --package ./passwords_otp-1.1.3.zip \
  --sha256 "$OTP_SHA" \
  --group 'otp-pilot' \
  --confirm-production \
  --ack-aio-backup \
  --accept-unapproved-rc \
  --accept-browser-token-risk
```

Expected: `AIO_INSTALL_PASS: 1.1.3`. The installer stages only `passwords_otp` in the persistent `custom_apps` volume, checks file hashes, enables the app through `occ` and verifies group scope. No SQL patch or container restart is intended.

If it prints `STOP`, **do not retry blindly**; inspect the transaction journal and effective app registration first.

## 4. Independent verification and browser acceptance

```sh
sudo python3 aio_install.py --verify \
  --package ./passwords_otp-1.1.3.zip \
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
  --package ./passwords_otp-1.1.3.zip \
  --sha256 "$OTP_SHA" \
  --confirm-production \
  --ack-aio-backup
```

After an AIO update, `--allow-aio-update-for-rollback` permits only an *explicitly confirmed* emergency disable of the exact app installation recorded by this tool. It verifies receipt, unchanged app files, registration and persistent volume, **but it does not restore the database**. Use the independent AIO backup if identity or state is uncertain.

## Earlier releases

For the historical `passwords_otp-1.0.0.zip` and its exact inputs, use
[the v1.0.0-tagged AIO procedure](https://github.com/RamonP12/nextcloud-passwords-otp-extension/blob/v1.0.0/docs/AIO_MANUAL_INSTALL.md).
