# Installation and version selection

## Current version: 1.1.2 Nextcloud Vue edition

Version 1.1.2 requires Passwords **2026.11.20**, installed and enabled, and adds
an installable TAR archive to the Vue edition. Use the [v1.1.2 GitHub Release](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.2),
its matching source tag and the [1.1.2 verification record](VALIDATION_1.1.2.md).
Historical tags, assets and acceptance records remain unchanged.

| Archive | Required tooling | Intended scope |
| --- | --- | --- |
| `passwords_otp-1.1.2.tar.gz` | Matching release checksum and `BUILD.json`; a tested manual deployment procedure | Current compiled single-root Nextcloud distribution, unsigned |
| `passwords_otp-1.1.2.zip` | Scripts from tag **`v1.1.2`**, matching `BUILD.json` | Current transactional localhost installer and scoped AIO first-install tooling |
| Published `passwords_otp-1.1.1.zip` | Scripts from tag **`v1.1.1`** | Historical Vue release; no new dependency lifecycle enforcement |
| Previously built `passwords_otp-1.1.0.zip` | Scripts from its exact source commit | Historical Vue candidate and its recorded local acceptance |
| Published `passwords_otp-1.0.0.zip` | `aio_install.py` and `release.py` from tag **`v1.0.0`** | Historical first-install procedure documented below |

**Current 1.1.2 scripts reject a 1.0.0 archive.** Never copy scripts from moving
`main` when installing an older release. The installer, archive version and build
manifest must agree. Older asset mappings exist only to verify and back up an
existing app and restore it on a failed local transaction; they do not make an
old archive a valid current installer input.

### Required Passwords dependency

The original Passwords app is a mandatory prerequisite. Its installed version
and on-disk metadata must both be **2026.11.20** and it must be enabled globally or for configured groups. Users also need individual access to both apps. An administrator
can enable OTP for all test users; this does not override Passwords group access.

- A fresh OTP registration fails when the prerequisite is absent, disabled or
  incompatible. Nextcloud may already have downloaded/extracted the OTP files
  before the application migration can check the prerequisite.
- An invalid activation is reversed. Disabling Passwords normally disables OTP.
- Removal without the normal disable event, including manual file deletion,
  is detected on later boot/runtime checks or the scheduled fallback. The
  five-minute job interval depends on an operational Nextcloud cron runner.
- Restoring Passwords does not re-enable OTP automatically. The administrator
  reviews the prerequisite and enables OTP explicitly.

Read [dependency lifecycle](DEPENDENCY_LIFECYCLE.md) for the exact event behavior,
recovery and timing limits. The migration checks prerequisites and adds no OTP
data tables, but Nextcloud migration/job bookkeeping is real state and must be
included in rollback verification.

### Obtain and verify the 1.1.2 distribution

Download the assets from the [tag-specific release page](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.2):

- `passwords_otp-1.1.2.tar.gz` and `passwords_otp-1.1.2.tar.gz.sha256`
- `passwords_otp-1.1.2.zip` and `passwords_otp-1.1.2.zip.sha256` if using the Python installer
- `BUILD.json`

In the download directory, verify the applicable archives:

```fish
sha256sum -c passwords_otp-1.1.2.tar.gz.sha256
sha256sum -c passwords_otp-1.1.2.zip.sha256
```

Each downloaded archive's check must print `OK`. Compare the digest with the
release's recorded SHA256 and confirm that `BUILD.json` identifies 1.1.2 and the
source revision behind `v1.1.2`. Both archives contain the same runtime payload
inside one `passwords_otp/` directory. GitHub's automatic **Source code** archives
are source snapshots and do not contain the compiled application.

A SHA256 checksum is not a Nextcloud signature. These ordinary GitHub artifacts
are unsigned and retain `production_approved=false`. A correctly formatted TAR
alone is insufficient for an App Store release; see [App Store packaging and
signing](APPSTORE_PACKAGING.md).

For a reproducible source build, check out the tag and follow [Development](DEVELOPMENT.md),
including a clean committed checkout and checked packaging. The app contains
`js/app-112.mjs` and `css/app-112.css`; Nextcloud does not need Node.js/npm at
runtime.

### Installation and acceptance scope

The maintainer-specific localhost tools (`scripts/local.py`, `scripts/deploy.py`)
target the existing loopback-only Docker Compose/MariaDB fixture. They verify
the current app, save a backup/journal, replace the app and verify installed
files and served assets. They retain prior Vue asset mappings for verification
and rollback and account for the new dependency bookkeeping. They are not
generic deployment scripts. See [Development](DEVELOPMENT.md) for fixture
constraints and [1.1.2 verification](VALIDATION_1.1.2.md) for actual evidence.

On 2026-11-19 the maintainer confirmed five manual checks on the 1.1.0 Vue
candidate: independent TOTP comparison, copying, search, persistent entry
creation and logout invalidation. Those checks remain historical frontend
acceptance. **1.1.2 changes server-side lifecycle behavior and needs additional
disposable localhost tests** for missing/disabled/incompatible Passwords,
activation, disable/remove handling, group separation and recovery. Do not
infer those results from unit fixtures or the five previous checks.

The AIO tool remains **first-install only**, with version/hash/scope/backup
gates. It refuses an existing OTP app, including 0.7.3. A 1.1.2 AIO first install
needs its matching source/archive, checksum and separate environment acceptance.
No production AIO/PostgreSQL in-place upgrade procedure is supplied. The
historical commands below apply only to the v1.0.0 tagged tools and archive.

## Published v1.0.0: historical installation procedure

**Distribution:** unsigned, unofficial GitHub source/release ZIP; not in the Nextcloud App Store. This is a manual **first-install** path, not a supported upgrade procedure.

**Release status (2026-11-11):** The exact published v1.0.0 ZIP passed a real manual installation into an existing disposable HTTPS localhost/Docker Compose/MariaDB Nextcloud fixture: **10/10 blocks, 49/49 checks**. A first install of this ZIP on **AIO/PostgreSQL** remains pending. See [local acceptance](LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md), [Validation](VALIDATION.md) and [release integrity](RELEASE_INTEGRITY_v1.0.0.md).

## Requirements

- Nextcloud **35.0.2** with the original **Passwords 2026.11.20** app enabled (tested API combination; wider compatibility unverified).
- PHP 8.3–8.5 according to app metadata, and a browser supporting WebCrypto.
- Backups of Nextcloud database and persistent application data, with a tested restoration procedure.
- For AIO: persistent writable `custom_apps` storage, PostgreSQL, local Docker Unix socket, Python 3.10+, and an existing group for restricted installation.

## Observed local installation (not a general-purpose non-AIO procedure)

The operator completely removed the internal local 0.7.3 app and installed the verified v1.0.0 ZIP into an already running Nextcloud 35.0.2.2 fixture. The original Passwords 2026.11.20 app remained unchanged and the OTP app was restricted to group `otp-v1-pilot`. The recorded 49 checks cover file integrity, CSE, TOTP reference, sharing, group access and session expiry/logout. This is evidence of **one local integration**, not certification of other environments or a turnkey installer.

## Published archive: use the verified v1.0.0 release ZIP

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

## Historical reproducibility: build from the pinned v1.0.0 tag

**Do not clone moving `main` to reproduce v1.0.0.** Current source includes the 1.1.2 Vue edition with additional dependency lifecycle checks. The source commit in `BUILD.json` also affects the package checksum, independently of runtime changes.

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
