# Installation – Passwort OTP Code Generator v1.0.0

**Distribution:** unsigned, unofficial GitHub source/release ZIP; not in the Nextcloud App Store. This is a manual **first-install** path, not a supported upgrade procedure.

**Automated v1.0.0 release checks passed; a real first-install test of the v1.0.0 package is still pending.** See [Validation](VALIDATION.md).

## Requirements

- Nextcloud **35.0.2** with the original **Passwords 2026.11.20** app enabled (tested API combination; wider compatibility unverified).
- PHP 8.3–8.5 according to app metadata, and a browser supporting WebCrypto.
- Backups of Nextcloud database and persistent application data, with a tested restoration procedure.
- For AIO: persistent writable `custom_apps` storage, PostgreSQL, local Docker Unix socket, Python 3.10+, and an existing group for restricted installation.

## Option A (recommended): use the verified v1.0.0 release ZIP

The [v1.0.0 GitHub Release](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.0.0) supplies exactly three files: `passwords_otp-1.0.0.zip`, `passwords_otp-1.0.0.zip.sha256`, and `BUILD.json`. The release link becomes available to the general public after the draft is published.

Download the assets into an empty local directory:

```sh
mkdir -p otp-release-v1.0.0
gh release download v1.0.0 \
  --repo RamonP12/nextcloud-passwords-otp-extension \
  --pattern 'passwords_otp-1.0.0.zip*' \
  --pattern 'BUILD.json' \
  --dir otp-release-v1.0.0
cd otp-release-v1.0.0
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

The app targets Nextcloud 35, but **no general-purpose non-AIO installation procedure is verified** for v1.0.0. The AIO installer is not a generic Docker or bare-metal installer.

## After installation

For an authorized user, open **Passwort OTP Code Generator** from the Nextcloud navigation. With synthetic OTP records, verify personal and shared TOTP, copying, creation, CSE challenges, login expiration and failure handling. Confirm that a user outside the configured group is denied access.

See [User guide](USER_GUIDE.md), [Compatibility](COMPATIBILITY.md) and [Security review](SECURITY_REVIEW.md).
