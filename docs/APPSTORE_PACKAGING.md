# Nextcloud App Store packaging (preparation only)

This repository already uses standard Nextcloud app directories (`appinfo/`,
`lib/`, `templates/`, `css/`, `js/`, `img/`). **Do not move them into a new
source root.** The App Store requirement applies to the **distribution archive**:
one root named `passwords_otp`, `appinfo/info.xml`, Nextcloud-signed application
files in `appinfo/signature.json`, and a separately signed `.tar.gz` archive.

This is an **additional, local-only release path**. It does not replace the
existing version-bound ZIP/AIO first-install procedure, modify published
`v1.0.0` assets, register the app, or authorize v1.0.1 publication.

## Trust boundary and gates

1. Finish the app's existing **version-specific** tests and validate
   `appinfo/info.xml` using the full official Nextcloud App Store XSD.
2. Build the existing ZIP from an exact, clean and reviewed source commit
   (`python3 scripts/release.py .build/package`). Record and independently
   verify its SHA256 and `BUILD.json` before using it here.
3. Stage exactly that ZIP with `scripts/appstore_package.py stage`. The tool
   checks the ZIP hash, manifest file hashes, identity/version, mandatory
   `<bugs>` and permitted production paths. It never includes source tests,
   `node_modules`, Git metadata, or signing keys.
4. **Outside the Codex agent**, use the **real Nextcloud signing certificate**
   and a trusted Nextcloud instance's `occ integrity:sign-app` to create
   `appinfo/signature.json` in the staged app. Never check a private key into
   Git or put it in `/home/codex-cli`.
5. Package the signed stage with `scripts/appstore_package.py package`. The
   tool refuses missing signatures, extra files, symlinks, modifications to
   the original ZIP payload and mismatched per-file SHA512 hashes. It builds
   a reproducible `.tar.gz` with only `passwords_otp/` as top-level directory
   and enforces a **20 MB** archive limit.
6. Verify the **cryptographic code signature** with Nextcloud's own
   `occ integrity:verify-app` in an isolated test instance. The packaging
   script checks **hash-list consistency only**, not certificate trust or
   cryptographic signature validity. Run normal install/update/rollback and
   security acceptance separately.
7. Sign the **exact final tar.gz bytes** with SHA512 and the private App Store
   key; upload the immutable, verified asset to a GitHub release and submit
   its HTTPS URL plus **archive signature** to the Nextcloud App Store.

Never edit files after step 4. Any modification requires signing the staged
files again and rebuilding/re-signing the archive. In particular,
`appinfo/signature.json` and the external tarball signature are **two distinct
signatures**.

## Commands (only after all version-specific tests and approvals)

On the reviewed release branch, in a trusted release-manager checkout:

```sh
# Produces ZIP + matching .sha256 + BUILD.json from the current tagged source.
python3 scripts/release.py .build/package

# Replace 1.0.1 with the actual newly approved version.
ZIP='.build/package/passwords_otp-1.0.1.zip'
ZIP_SHA="$(sha256sum "$ZIP" | cut -d ' ' -f1)"
python3 scripts/appstore_package.py stage \
  --zip "$ZIP" --sha256 "$ZIP_SHA" \
  --output .build/appstore/stage
```

**STOP:** The following step requires a Nextcloud-issued app-signing certificate
whose CN is `passwords_otp`. Run this in the trusted signing environment,
not in a Codex shell or a production Nextcloud instance:

```sh
php /path/to/disposable-nextcloud/occ integrity:sign-app \
  --privateKey=/secure/private/passwords_otp.key \
  --certificate=/secure/public/passwords_otp.crt \
  --path="$(pwd)/.build/appstore/stage/passwords_otp"
```

After checking `appinfo/signature.json` and verifying the signature with a
disposable Nextcloud instance:

```sh
TAR='.build/appstore/passwords_otp-1.0.1.tar.gz'
python3 scripts/appstore_package.py package \
  --zip "$ZIP" --sha256 "$ZIP_SHA" \
  --signed-app-dir .build/appstore/stage/passwords_otp \
  --output "$TAR"
sha256sum "$TAR"

# Required *separate* signature of the exact tarball bytes.
openssl dgst -sha512 -sign /secure/private/passwords_otp.key "$TAR" \
  | openssl base64 -A > "$TAR.sig"
```

The `.sig` file is a **base64-encoded SHA512/RSA signature** to supply to the
App Store, **not** the same as the `.sha256` digest used for human integrity
checks. Keep it with the final archive. The final source commit, Nextcloud
certificate ownership, release gates, published asset identity and release
immutability must be reviewed independently.

## Non-goals and known blockers

- No GitHub Actions minutes required. Unit tests: `python3 -m unittest
  discover -s tests/python -v`.
- No changes to token privileges or to internal Nextcloud Passwords PHP
  integration. These are tracked independently in **issue #1 / AP23** and
  remain material App Store security/API-review risks.
- No App Store registration, certificate request, signed real build or
  installation acceptance is claimed by this change.
- `v1.0.0` lacks mandatory `<bugs>` metadata and must not be repackaged as an
  App Store release. The unreleased v1.0.1 candidate still needs its full
  release-specific tests.
- The existing AIO installer accepts its own verified **ZIP**, not this tarball.
  The two release channels remain separate until a tested, approved migration.

## Official references

- [Nextcloud release process](https://docs.nextcloud.com/server/stable/developer_manual/app_publishing_maintenance/release_process.html)
- [Nextcloud code signing](https://docs.nextcloud.com/server/stable/developer_manual/app_publishing_maintenance/code_signing.html)
- [Nextcloud App Store developer guide](https://nextcloudappstore.readthedocs.io/en/latest/developer.html)
- [Nextcloud App Store release API](https://nextcloudappstore.readthedocs.io/en/latest/api/restapi.html)
