# Installation – Passwort OTP Code Generator v1.0.0

**Distribution:** unsigned, unofficial GitHub source/release ZIP; not in the Nextcloud App Store. This is a manual **first-install** path, not a supported upgrade procedure.

**Release status (2026-11-11):** The exact published v1.0.0 ZIP passed a real manual installation into an existing disposable HTTPS localhost/Docker Compose/MariaDB Nextcloud fixture: **10/10 blocks, 49/49 checks**. A first install of this ZIP on **AIO/PostgreSQL** remains pending. See [local acceptance](LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md), [Validation](VALIDATION.md) and [release integrity](RELEASE_INTEGRITY_v1.0.0.md).

## Requirements

- Nextcloud **35.0.2** with the original **Passwords 2026.11.20** app enabled (tested API combination; wider compatibility unverified).
- PHP 8.3–8.5 according to app metadata, and a browser supporting WebCrypto.
- Backups of Nextcloud database and persistent application data, with a tested restoration procedure.
- For AIO: persistent writable `custom_apps` storage, PostgreSQL, local Docker Unix socket, Python 3.10+, and an existing group for restricted installation.

## Observed local installation (not a general-purpose non-AIO procedure)

The operator completely removed the internal local 0.7.3 app and installed the verified v1.0.0 ZIP into an already running Nextcloud 35.0.2.2 fixture. The original Passwords 2026.11.20 app remained unchanged and the OTP app was restricted to group `otp-v1-pilot`. The recorded 49 checks cover file integrity, CSE, TOTP reference, sharing, group access and session expiry/logout. This is evidence of **one local integration**, not certification of other environments or a turnkey installer.

## Option A (recommended): use the verified v1.0.0 release ZIP

The [v1.0.0 GitHub Release](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.0.0) supplies exactly three files: `passwords_otp-1.0.0.zip`, `passwords_otp-1.0.0.zip.sha256`, and `BUILD.json`. The release was published on 2026-11-11; these three asset names and their SHA256 digests were verified against GitHub's release metadata.

The assets can be downloaded directly from the **public** release, without an authenticated GitHub CLI. Use the following stable, tag-specific download URLs:

- [passwords_otp-1.0.0.zip](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/download/v1.0.0/passwords_otp-1.0.0.zip)
- [passwords_otp-1.0.0.zip.sha256](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/download/v1.0.0/passwords_otp-1.0.0.zip.sha256)
- [BUILD.json](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/download/v1.0.0/BUILD.json)

Alternatively, download all three files using `curl`:

```sh
mkdir -p otp-release-v1.0.0
cd otp-release-v1.0.0
BASE='https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/download/v1.0.0'
curl --fail --location --remote-name "$BASE/passwords_otp-1.0.0.zip"
curl --fail --location --remote-name "$BASE/passwords_otp-1.0.0.zip.sha256"
curl --fail --location --remote-name "$BASE/BUILD.json"
sha256sum -c passwords_otp-1.0.0.zip.sha256
printf '%s  %s\n' \
  'ffc002d7c41485cac4a4b7eb27659fd5d5dbbd4bd7fd40d78e3ea91373a12256' \
  'passwords_otp-1.0.0.zip' | sha256sum -c -
```

Both integrity checks **must** print `OK`. Verify that `BUILD.json` identifies commit `56d6de06e4825c9bd03b4b07dec5825d64228390` and `production_approved=false`. The ZIP's own manifest is also integrity protected by the checked archive hash.

Obtain the two AIO installer scripts **from this exact same tagged source revision**; do not take them from `main` or another version:

```sh
git clone --depth 1 --branch v1.0.0 \
  https://github.com/RamonP12/nextcloud-passwords-otp-extension.git \
  ../otp-v1.0.0-source
test "$(git -C ../otp-v1.0.0-source rev-parse HEAD)" = \
  '56d6de06e4825c9bd03b4b07dec5825d64228390'
cp ../otp-v1.0.0-source/scripts/aio_install.py .
cp ../otp-v1.0.0-source/scripts/release.py .
```

Transfer the verified ZIP and these **two matching scripts** to a private directory on the AIO host, then follow [AIO installation and rollback](AIO_MANUAL_INSTALL.md). Keep the SHA256 file and `BUILD.json` for your audit record.

## Option B: independently build from the immutable v1.0.0 tag

**Do not clone moving `main` to reproduce v1.0.0.** It contains documentation-only updates after the release commit, and the source commit in `BUILD.json` affects the package checksum.

```sh
git clone --depth 1 --branch v1.0.0 \
  https://github.com/RamonP12/nextcloud-passwords-otp-extension.git
cd nextcloud-passwords-otp-extension
test "$(git rev-parse HEAD)" = \
  '56d6de06e4825c9bd03b4b07dec5825d64228390'
npm ci
npm test
npm run test:client
python3 -m unittest discover -s tests/python -v
npm run build
python3 scripts/release.py .build/package
sha256sum .build/package/passwords_otp-1.0.0.zip
```

Use the source tree and installer scripts **from the same tag**. Rebuilding on a different commit produces a **different manifest and archive hash** even when the application runtime is identical. For the externally verified ZIP, the expected SHA256 is the value above; do not substitute a hash from another source revision.

## First-time installation on Nextcloud AIO

Follow the complete [AIO manual installation guide](AIO_MANUAL_INSTALL.md), including:

1. Verify an actual full backup and a restoration procedure.
2. Select an existing limited pilot group; `--all-users` is not a substitute.
3. Supply the verified ZIP and `scripts/aio_install.py` plus `scripts/release.py` **from tag `v1.0.0`**.
4. Run `--inspect`, followed by the ZIP- and group-bound `--preflight`.
5. Explicitly acknowledge the residual WebUI bearer-token risk before `--install`.
6. Verify app files, access scope, in-group operation and out-of-group denial in real browsers.

**The first-install tool refuses an existing `passwords_otp` installation, including 0.7.3 (an earlier internal version).** Do not attempt to overwrite, upgrade or roll back an unrelated pre-existing installation using this tool.

## Non-AIO installations

The app targets Nextcloud 35. The published ZIP was successfully deployed in **one local maintainer-specific Docker Compose/MariaDB test environment**, but **no generally supported or documented non-AIO installation procedure** has been released for v1.0.0. The AIO installer is not a generic Docker or bare-metal installer.

## After installation

For an authorized user, open **Passwort OTP Code Generator** from the Nextcloud navigation. With synthetic OTP records, verify personal and shared TOTP, copying, creation, CSE challenges, login expiration and failure handling. Confirm that a user outside the configured group is denied access.

See [User guide](USER_GUIDE.md), [Compatibility](COMPATIBILITY.md) and [Security review](SECURITY_REVIEW.md).
