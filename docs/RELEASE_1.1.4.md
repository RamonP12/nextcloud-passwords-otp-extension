# Passwords OTP Generator 1.1.4

## Changes since v1.1.3

- The interface selects German or English from the browser's language preferences. English is the fallback. The Nextcloud shell uses its own settings.
- The vault follows the Passwords inactivity duration and keepalive mode. It clears protected state when the local deadline expires.
- OTP checks Passwords when serving requests. A compatible dependency can restore access after a reload, with the existing OTP group or all-user scope. If the administrator or v1.1.3 already disabled OTP, activate it explicitly.
- The creation dialog warns when a tab switch clears its password or OTP secret. CSE creation sends the SHA-1 prefix requested by Passwords and stops before writing if the setting cannot be validated.
- The copy controls show when session verification is pending after a window change. Copy with a fresh click once the code reappears.
- The Node 22 package-build fix, versioned `app-114` assets, isolated Vite output and GitHub Actions regression checks are included.

The [changelog](../CHANGELOG.md) links the user, compatibility and development guides.

## Compatibility and upgrade

| Scope | Requirement or behavior |
| --- | --- |
| Nextcloud and PHP | Nextcloud 35 with PHP 8.3–8.5 as declared in app metadata |
| Passwords at runtime | Installed and enabled stable build 2026.11.20–2026.11.29 with matching metadata and the reviewed interfaces |
| Passwords in the installer tools | Exact reviewed build 2026.11.20 |
| Upgrade from v1.1.3 | The Nextcloud application version increases. No OTP data table or stored-record conversion is introduced. Nextcloud tracks app migrations and the legacy dependency job. |
| Development package 1.2.0-dev | Nextcloud compares it as newer than 1.1.4. Use a separate fixture for 1.1.4 testing if 1.2.0-dev is installed. |

Use the same version for the archive and installer tooling. For a clean build on
the dedicated localhost Docker fixture, use Node 22.12+ within 22.x or Node 24,
then run the [local build and checks](DEVELOPMENT.md#local-checks). Follow the
same command sequence as in the [localhost upgrade procedure](INSTALLATION.md#upgrade-the-existing-localhost-test-fixture)
with 1.1.4 source. Expected post-install markers are `INSTALL_PASS: version=1.1.4`
and `HTTP_ASSETS_PASS: app-114`. Verify vault unlock, an existing entry, code
rotation, copying and creation with test data.

On AIO, record the OTP app activation and group scope before upgrading the
test installation. Follow the version-specific [dependency recovery guidance](DEPENDENCY_LIFECYCLE.md).
The Python AIO tool is for a scoped first install. It rejects installations that
already contain OTP. Production acceptance recorded for v1.1.3 is documented
in its [verification record](VALIDATION_1.1.3.md).

## Download and verification

Use the compiled `passwords_otp-1.1.4.tar.gz` or
`passwords_otp-1.1.4.zip` and its corresponding SHA-256 file. Run
`sha256sum -c` on the downloaded checksum file and verify that `BUILD.json`
identifies 1.1.4 and the release source commit. The compiled archives contain the
same runtime files. GitHub's source snapshots require a local build.

See [development](DEVELOPMENT.md#compare-a-rebuild-with-a-release) for content
verification when rebuilding with a different compression library. Release
verification results and the exact package hashes belong to the GitHub
release record.

[App Store signing and submission](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/14)
and the [upstream WebUI token scope](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1)
are tracked separately. The GitHub packages carry `production_approved=false`.
