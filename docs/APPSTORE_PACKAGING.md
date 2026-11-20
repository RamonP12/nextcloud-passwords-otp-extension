# Nextcloud tar.gz distribution and App Store signing

## Status of 1.1.3

Use the [published v1.1.3 packages](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.3) and their matching source and tooling. That version builds an installable `passwords_otp-1.1.3.tar.gz` in addition to
the ZIP used by the existing transactional localhost installer. Both ordinary
artifacts contain the same verified runtime files, production JS/CSS, licence
notices and `BUILD.json`, under exactly one `passwords_otp/` directory.

**The ordinary GitHub tar.gz is unsigned and intended for manual installation.**
Its format is suitable for the Nextcloud release flow; this does not make it a
published or signed App Store release. `production_approved` remains `false`.
No Nextcloud-issued signing certificate or corresponding private key was
provided for this release. No App Store registration or publication was performed.
The [verified GitHub release attestation](VALIDATION_1.1.3.md#github-release-integrity)
binds the Git tag and all attached assets. The remaining signing and Store acceptance work is tracked in [#14](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/14).

The GitHub-generated **Source code (tar.gz)** is a source snapshot, not this
installable artifact. It lacks the compiled assets and uses GitHub's versioned
directory name. Use the explicitly attached `passwords_otp-1.1.3.tar.gz`.

## What is verified

`scripts/release.py` creates the ordinary TAR from the exact verified ZIP
payload. `scripts/appstore_package.py` is also usable independently:

```fish
set commit (git rev-parse HEAD)
set package_dir ".build/$commit/package"
set zip "$package_dir/passwords_otp-1.1.3.zip"
set zip_sha (sha256sum "$zip" | string split ' ' | head -n 1)

# Alternative output path: the normal release build already produces its TAR.
python3 scripts/appstore_package.py unsigned \
    --zip "$zip" --sha256 "$zip_sha" \
    --output .build/passwords_otp-1.1.3-manual.tar.gz
```

The ZIP gate checks the current version's exact runtime allowlist and manifest.
The TAR gate checks identical bytes, a single app root, bounded compressed and
expanded size, file modes, directory set, and complete contents. It rejects
duplicate names, traversal, additional roots, links, devices, unexpected owners,
extra files and hidden trailing archives. Metadata and gzip timestamps are fixed;
two constructions must be byte-identical. The 20 MB compressed limit is decimal
and therefore no larger than the documented App Store limit.

There are two different signatures in the Store workflow:

| Signature | What it covers | Verification |
| --- | --- | --- |
| `appinfo/signature.json` | The signed runtime file inventory | Nextcloud code integrity check and the Nextcloud signing trust roots |
| Detached Base64 SHA512 signature | The final compressed tar.gz bytes | App Store download verification using the registered application certificate |

A SHA256 checksum proves byte identity relative to a known checksum. It is not
either of these signatures. A GitHub commit/tag signature also does not replace
Nextcloud signing.

## Future signing procedure

Use a controlled release host with a working Nextcloud 35 instance, PHP,
OpenSSL and the Nextcloud-issued certificate for `passwords_otp`. The private key
must remain outside the repository, package and signed staging directory. The
script never reads private keys, creates certificates, contacts the Store, or
uploads files. Store ownership registration requires the legitimate key holder
and is a separate prerequisite.

The following Fish example assumes the ZIP variables above are set. Replace
`/absolute/path/to/nextcloud/occ` with a working Nextcloud installation on the
release host. A Docker-only installation must make the staging directory and
signing material available securely to its PHP process; do not paste private keys
into commands or chat.

```fish
set stage .build/appstore-signing-1.1.3
set app "$stage/passwords_otp"
set occ /absolute/path/to/nextcloud/occ
set key ~/.nextcloud/certificates/passwords_otp.key
set certificate ~/.nextcloud/certificates/passwords_otp.crt
set signed_tar .build/passwords_otp-1.1.3-signed.tar.gz

python3 scripts/appstore_package.py stage \
    --zip "$zip" --sha256 "$zip_sha" --output "$stage"
and php "$occ" integrity:sign-app \
    --path "$app" --privateKey "$key" --certificate "$certificate"
and python3 scripts/appstore_package.py package \
    --zip "$zip" --sha256 "$zip_sha" --signed-app-dir "$app" \
    --occ "$occ" --output "$signed_tar"
```

The packaging command requires exactly the original files plus
`appinfo/signature.json`. It verifies the hash inventory and RSA-PSS signature,
then invokes the actual `integrity:check-app passwords_otp --path ...` command.
Nextcloud verifies certificate trust and scope; missing or failed checks stop
packaging. The signed directory is reread afterwards to detect intervening
changes. An unsigned app cannot accidentally pass through Nextcloud's
“no signature, skip check” path because the package gate requires the signature.

Nextcloud 35 uses **relative paths without a leading slash** in its signed hash
inventory. Its code-signature algorithm and JSON encoding differ from the
detached archive signature. This implementation follows the versioned core
source and corrects the incompatible leading-slash assumption in draft PR #9.

After successful signed packaging, create and verify the detached signature:

```fish
openssl dgst -sha512 -sign "$key" -out "$signed_tar.sig" "$signed_tar"
and openssl base64 -A -in "$signed_tar.sig" -out "$signed_tar.sig.base64"
and set tar_sha (sha256sum "$signed_tar" | string split ' ' | head -n 1)
and python3 scripts/appstore_package.py verify-detached \
    --archive "$signed_tar" --sha256 "$tar_sha" \
    --signature "$signed_tar.sig.base64" --certificate "$certificate"
```

`verify-detached` checks the SHA256 and cryptographic archive signature. It
explicitly reports **certificate trust not checked**: it does not replace the
earlier Nextcloud check, registered App Store ownership, or the Store's checks.
Use the same certificate for both signing stages. Never change the signed app
files or TAR after signing. Rebuild and sign again if any byte changes.

For an approved future distribution, attach the exact signed TAR before publishing its release. The published v1.1.3 assets are immutable. Verify the downloaded
checksum and submit the HTTPS URL and its detached signature to the registered App
Store account. Do not substitute the unsigned ordinary artifact or GitHub's
source snapshot. This repository does not automate publishing or consume
GitHub Actions minutes.

## Compatibility boundaries and evidence

The public App Store metadata must still satisfy the applicable schema and
policy. Passwords is a required companion, and 1.1.3 enforces its documented
dependency policy. That enforcement does not turn Passwords-internal PHP
classes into a supported public API. Upstream API stability and the token
privilege boundary remain separate review topics.

The packaging tests use synthetic payloads and short-lived, self-signed RSA
certificates created in a temporary directory. They test real OpenSSL signature
verification, forged signatures, altered payloads, hostile archives and
rejection at the trust gate. Test keys are deleted and are never release inputs.
No test fixture is evidence of a Nextcloud-issued certificate or Store approval.

## Primary references

- [Nextcloud 35 release process](https://docs.nextcloud.com/server/stable/developer_manual/app_publishing_maintenance/release_process.html)
- [App Store developer guide: certificate, registration, release and archive structure](https://nextcloudappstore.readthedocs.io/en/latest/developer.html)
- [App Store REST API: HTTPS download, size and detached signature](https://nextcloudappstore.readthedocs.io/en/stable/api/restapi.html)
- [Nextcloud 35.0.2 code-signature format and certificate trust checks](https://github.com/nextcloud/server/blob/v35.0.2/lib/private/IntegrityCheck/Checker.php)
- [Nextcloud 35.0.2 integrity:check-app command, including forced verification and unsigned skip](https://github.com/nextcloud/server/blob/v35.0.2/core/Command/Integrity/CheckApp.php)
- [Nextcloud code-signing documentation](https://docs.nextcloud.com/server/stable/developer_manual/app_publishing_maintenance/code_signing.html)
