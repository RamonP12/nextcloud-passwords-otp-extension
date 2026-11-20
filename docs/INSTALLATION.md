# Installation and version selection

For version 1.1.4, see the [release and upgrade notes](RELEASE_1.1.4.md).

## Published GitHub release 1.1.3

[Version 1.1.3](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.3)
requires Nextcloud 35, PHP 8.3–8.5 and Passwords **2026.11.20**. Use the
[`v1.1.3` source tag](https://github.com/RamonP12/nextcloud-passwords-otp-extension/tree/v1.1.3)
for the installer and the [1.1.3 verification record](VALIDATION_1.1.3.md) for
the tested combinations.

| Archive | Required tooling | Intended scope |
| --- | --- | --- |
| `passwords_otp-1.1.3.tar.gz` | Matching release checksum, `BUILD.json` and a tested manual deployment procedure | Current compiled single-root Nextcloud distribution, unsigned |
| `passwords_otp-1.1.3.zip` | Scripts from tag **`v1.1.3`**, matching `BUILD.json` | Current transactional localhost installer and scoped AIO first-install tooling |
| Published `passwords_otp-1.1.2.zip` or `passwords_otp-1.1.2.tar.gz` | Scripts from tag **`v1.1.2`** and its release checksums | Historical dependency-lifecycle release |
| Published `passwords_otp-1.1.1.zip` | Scripts from tag **`v1.1.1`** | Historical Vue release; no new dependency lifecycle enforcement |
| Previously built `passwords_otp-1.1.0.zip` | Scripts from its exact source commit | Historical Vue candidate and its recorded local acceptance |
| Published `passwords_otp-1.0.0.zip` | `aio_install.py` and `release.py` from tag **`v1.0.0`** | Historical first-install procedure documented below |

**Current 1.1.3 scripts reject a 1.0.0 archive.** Never copy scripts from moving
`main` when installing an older release. The installer, archive version and build
manifest must agree. Older asset mappings exist only to verify and back up an
existing app and restore it on a failed local transaction; they do not make an
old archive a valid current installer input.

### Required Passwords dependency in the published 1.1.3 package

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

See [dependency lifecycle](DEPENDENCY_LIFECYCLE.md) for the published behavior and the 1.1.4 behavior. The migration checks prerequisites and adds no OTP
data tables, but Nextcloud migration/job bookkeeping is real state and must be
included in rollback verification.

### Obtain and verify the 1.1.3 distribution

Download the assets from the [tag-specific release page](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.3):

- `passwords_otp-1.1.3.tar.gz` and `passwords_otp-1.1.3.tar.gz.sha256`
- `passwords_otp-1.1.3.zip` and `passwords_otp-1.1.3.zip.sha256` if using the Python installer
- `BUILD.json`

In the download directory, verify the applicable archives:

```fish
sha256sum -c passwords_otp-1.1.3.tar.gz.sha256
sha256sum -c passwords_otp-1.1.3.zip.sha256
```

Each downloaded archive's check must print `OK`. Compare the digest with the
release's recorded SHA256 and confirm that `BUILD.json` identifies 1.1.3 and the
source revision behind `v1.1.3`. Both archives contain the same runtime payload
inside one `passwords_otp/` directory. GitHub's automatic **Source code** archives
are source snapshots and do not contain the compiled application.

The [verified GitHub release attestation](VALIDATION_1.1.3.md#github-release-integrity)
binds the release tag and assets. The packages retain `production_approved=false`.
Nextcloud certificate signing and App Store distribution have their own
requirements. See [App Store packaging and signing](APPSTORE_PACKAGING.md).

For a source rebuild, check out the tag and follow [Development](DEVELOPMENT.md#compare-a-rebuild-with-a-release),
including a clean committed checkout and checked packaging. The app contains
`js/app-113.mjs` and `css/app-113.css`. Node.js and npm are build-time tools.

### Installation and acceptance scope

The [1.1.3 verification record](VALIDATION_1.1.3.md) documents the maintainer’s
upgrade from 1.1.2 on the existing Docker Compose/MariaDB fixture and the
separate SQLite upgrade and rollback. The earlier [1.1.2 localhost acceptance](LOCAL_ACCEPTANCE_v1.1.2_2026-11-19.md)
covers the ordinary Passwords disable and re-enable flow. The [lifecycle test plan](DEPENDENCY_LIFECYCLE.md#verification-and-remaining-installed-server-acceptance)
covers the remaining scenarios.

#### Upgrade the existing localhost test fixture

From a clean checkout of the `v1.1.3` tag, use Node 24 for the complete build
and the browser, Playwright environment and PHP image described in
[Development](DEVELOPMENT.md). The build creates a
local, commit-bound package and receipt. Run the steps in order:

```fish
python3 scripts/local.py --build
and python3 scripts/local.py --preflight
and python3 scripts/local.py --install
and python3 scripts/local.py --verify
```

Expect `BUILD_PASS`, `LOCALHOST_PREFLIGHT_PASS`, `INSTALL_PASS: version=1.1.3`
and `LOCALHOST_VERIFY_PASS`. After install, `HTTP_ASSETS_PASS` should identify
`app-113`. Record the transaction path printed by `BACKUP_PASS`. Open the app
in Nextcloud and verify unlock, search, code copying and creation with synthetic
data. See the [user guide](USER_GUIDE.md) for the two copy controls.

For a completed transaction that needs to be reversed, provide its own backup
path:

```fish
python3 scripts/deploy.py --localhost-test-only --rollback '/absolute/path/from/BACKUP_PASS'
```

#### Install on a separate AIO/PostgreSQL test fixture

The [AIO guide](AIO_MANUAL_INSTALL.md) documents version-matched first-install
tooling, preflight and rollback. The installer refuses an existing OTP app,
including 0.7.3. The [1.1.3 verification record](VALIDATION_1.1.3.md) covers
PostgreSQL/Redis lab tests and a separate manual production AIO replacement.
Full-stack AIO first-install tooling and production rollback verification remain open.

For an existing OTP deployment, use the [post-upgrade check and recovery](VALIDATION_1.1.3.md#post-upgrade-check-and-recovery)
after an AIO core upgrade. One production upgrade to Nextcloud 35.0.3 required
manual OTP activation after Passwords was active.

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

**Do not clone moving `main` to reproduce v1.0.0.** Current source includes the newer Vue edition, prerequisite checks and a different package inventory. The source commit in `BUILD.json` also affects the package checksum, independently of runtime changes.

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
