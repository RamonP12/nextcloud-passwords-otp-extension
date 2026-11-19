# Version 1.1.3 release and verification

GitHub published [v1.1.3](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.3) as the latest release on 2026-11-19. The tag points to the [PR #15 squash commit](https://github.com/RamonP12/nextcloud-passwords-otp-extension/commit/ae1096099521dcf9bf7bc6f5e5011f88bced5916) and GitHub reports the release as immutable. The release adds the **Passwords OTP Generator** name, shield icon and direct code copying. The internal app ID is `passwords_otp`.

## Published packages

Use the compiled ZIP for the version-matched installer tooling and the compiled TAR.GZ for manual distribution. Each archive contains the same 18 files inside one `passwords_otp/` root. The attached `BUILD.json` identifies app version 1.1.3, records the source commit and lists the runtime file hashes. All five release attachments were downloaded after publication and matched the build outputs byte for byte.

| Archive | SHA-256 |
| --- | --- |
| `passwords_otp-1.1.3.zip` | `92021a9bc69d3a12378fc33de483fdb0806cacc240269a08b350234846a469dd` |
| `passwords_otp-1.1.3.tar.gz` | `2019ff98d6decadc7fbbd14f3a486a9b3a7898a407fa5bfe3cd82b91f94197cc` |

The GitHub artifacts are unsigned Nextcloud packages with `production_approved=false`. Archive checksums verify byte identity. Independent cryptographic verification of the GitHub release attestation is tracked in [#3](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/3). Nextcloud certificate signing and App Store submission are tracked in [#14](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/14). Cross-environment archive reproducibility is tracked in [#16](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/16).

## Verification by environment

| Environment | Observed result |
| --- | --- |
| Build from the published merge commit | 238 JavaScript tests, 17 upstream-client tests and 102 Python tests passed. The build gate completed both bundle builds and the deterministic packaging checks. npm audit reported zero vulnerabilities. |
| Compiled browser suites | Chromium and Firefox each passed 32 cases with synthetic API, shell and clipboard fixtures. Cases cover direct code click, keyboard activation, leading zeroes, clipboard errors, near-expiry denial and the icon at 16, 24 and 32 pixels. Bundle hashes matched the merge-commit build. |
| PHP and pinned Nextcloud core components | On PHP 8.4.27, the security and dependency suites passed 67 and 110 assertions, 13 PHP files passed syntax checks, the app metadata validated against the Nextcloud 35.0.2 XSD, and 24 lifecycle component cases passed with service doubles. |
| Maintainer preflight | Nextcloud 35.0.2 (internal 35.0.2.2), PHP 8.5.12, MariaDB and Passwords 2026.11.20. PHP contracts and all 32 compiled browser cases passed. The preflight verified the installed 1.1.2 assets before the upgrade. |
| Maintainer upgrade and manual acceptance | The 1.1.2 → 1.1.3 transaction created and verified a backup. Installed files and served `app-113` assets passed post-install verification. The maintainer confirmed unlocking the vault, finding existing OTP entries, copying codes and creating a test entry. The screenshot showed the new name and shield icon. |
| Separate real-server fixture | On Nextcloud 35.0.2 / PHP 8.4.27 / SQLite with Passwords 2026.11.20, the upgrade retained an existing synthetic entry. The app name in the Apps list and browser title, served SVG, both copy controls and creation passed. A manual rollback to 1.1.2 retained both synthetic entries. |

The maintainer installed a package built from the [reviewed PR head](https://github.com/RamonP12/nextcloud-passwords-otp-extension/commit/9120b4189a16808cbb0961fa58bf343688471c6b). The published archive was built after the squash merge. The Git trees are identical. Each build manifest records its own commit, so use the published release checksums when verifying downloads.

The [dependency lifecycle](DEPENDENCY_LIFECYCLE.md) lists the negative cases still requiring live checks. Signed App Store installation remains open.

## PostgreSQL and Redis verification

The exact published ZIP was exercised with real Nextcloud, Passwords 2026.11.20, PHP 8.4.27, PostgreSQL 18.6 and Redis locking on isolated fixtures. These used a local PHP server and HTTPS proxy. The AIO installer was tested separately with Docker doubles.

| Environment | Observed result |
| --- | --- |
| Nextcloud 35.0.2 | Fresh installation, 1.1.2 → 1.1.3 replacement and rollback to 1.1.2 passed. Synthetic records created before and after replacement were visible after rollback. |
| Nextcloud 35.0.2 browser | The independent TOTP reference, both clipboard controls, search, account creation, real read-only incoming share, CSE unlock and encrypted creation, session expiry and denial outside the OTP group passed. |
| Nextcloud 35.0.3 | Fresh installation, OTP creation, clipboard, search, session expiry and OTP group denial passed. Disabling Passwords disabled OTP. Re-enabling Passwords required a separate explicit OTP activation. |
| AIO first-install tooling | 29 automated AIO installer cases passed using Docker doubles. |

The first write attempt using database-backed file locking failed in the original Passwords backend with a value-length error in `oc_file_locks`. Repeating with Redis locking allowed writes. The Passwords program files matched before and after the replacement and rollback tests. See [Nextcloud transactional file locking](https://docs.nextcloud.com/server/stable/admin_manual/configuration_files/files_locking_transactional.html) and [Nextcloud AIO](https://github.com/nextcloud/all-in-one).

## Maintainer-confirmed production AIO replacement (2026-11-19)

One Nextcloud AIO installation ran Nextcloud **35.0.2** (internal **35.0.2.2**), PHP **8.4.27**, PostgreSQL, `OC\Memcache\Redis` locking and Passwords **2026.11.20**. Before the change, Nextcloud reported `maintenance=false` and `needsDbUpgrade=false`. The `passwords` and `passwords_otp` apps were both active for all users under `custom_apps`. The installed OTP version was the internal **0.7.3** and its metadata declared no uninstall steps.

1. The operator verified the published **1.1.3 TAR.GZ** against the SHA-256 above, unpacked it into temporary staging and staged its application files on the container's `custom_apps` filesystem. The staged application files were assigned to `33:0`, with directories readable and traversable by the web server.
2. The operator disabled `passwords_otp`, removed 0.7.3 via `occ app:remove --keep-data passwords_otp`, moved the staged application directory into place and activated it via `occ app:enable passwords_otp`. The existing all-user scope was preserved. The operator chose to proceed without creating a separate archive of the prior app files or an app-specific configuration export.
3. OCC verified `passwords_otp` **1.1.3**, enabled value `yes`, the expected app path, and `passwords` **2026.11.20** still active. The maintainer reported the browser checks succeeded and explicitly confirmed that both a personal and an incoming shared entry displayed correctly. The maintainer also confirmed the transparent key cut-out in the Apps administration view after bypassing the browser cache.

### Apps administration icon cache

The Apps view initially showed a solid shield after repeated page reloads. The installed `img/app.svg` matched the v1.1.3 release SVG (SHA-256 `dfd4155be2d0217e2a0d2eabc1afb50b880b529f9c9c8d6e0c1914887b639499`). A direct request to that SVG with a fresh query parameter displayed the key. The maintainer then opened **Apps → F12 → Network → Disable cache**, reloaded with DevTools open and confirmed the key in the app details. Nextcloud fetches the SVG separately in the [Apps list](https://github.com/nextcloud/server/blob/v35.0.2/apps/appstore/src/components/AppIcon.vue) and configures long-lived caching for [static SVG assets](https://github.com/nextcloud/server/blob/v35.0.2/.htaccess#L46-L54).

This records one manual production replacement and its operator acceptance. A production rollback, a fresh install using the AIO installer against the full container stack, and signed App Store installation remain open. The AIO installer continues to reject existing OTP installations. See [AIO first-install tooling](AIO_MANUAL_INSTALL.md).

## Production AIO core upgrade and OTP reactivation

On 2026-11-19 the operator reported upgrading the same installation to AIO **15.1.1**. The AIO log recorded the Nextcloud core upgrade from **35.0.2.2 to 35.0.3.2** and a subsequent failed activation of `passwords_otp` before AIO activated `passwords`. This sequence matches the OTP activation guard for an inactive dependency. The exact exception from the first activation attempt was unavailable.

After AIO completed, the operator successfully ran `occ app:enable passwords_otp` and confirmed that existing OTP entries displayed, codes rotated and copying worked. OCC reported Nextcloud **35.0.3**, `maintenance=false`, `needsDbUpgrade=false`, Passwords **2026.11.20** and OTP **1.1.3**, both with `enabled=yes`. This verifies one production core upgrade with manual OTP recovery. See [AIO 15.1.1 app restoration](https://github.com/nextcloud/all-in-one/blob/v15.1.1/Containers/nextcloud/entrypoint.sh#L521-L550) and [OTP activation enforcement](https://github.com/RamonP12/nextcloud-passwords-otp-extension/blob/v1.1.3/lib/Listener/PasswordsLifecycleListener.php).

### Post-upgrade check and recovery

Record the OTP app's `enabled` value before an AIO core upgrade. After AIO has finished, check core status and both app versions and activation scopes on the AIO host.

```sh
otp_occ() {
  sudo docker exec --user www-data nextcloud-aio-nextcloud \
    php /var/www/html/occ "$@"
}

otp_occ status --output=json
for app in passwords passwords_otp; do
  printf '\n%s\n' "$app"
  otp_occ config:app:get "$app" installed_version
  otp_occ config:app:get "$app" enabled
done
```

If OTP was active before the upgrade and is now disabled, verify that maintenance and database upgrade are complete and that Passwords **2026.11.20** is installed and active for the intended users. For a prior all-user scope (`yes`), run `otp_occ app:enable passwords_otp`. For a prior group scope, pass the original group IDs using `--groups` on the enable command. Verify the resulting scope and check an existing OTP entry, code rotation and clipboard copy in the browser. Investigate a remaining activation error with the full OCC error and the [dependency requirements](DEPENDENCY_LIFECYCLE.md). See [Nextcloud OCC app commands](https://docs.nextcloud.com/server/stable/admin_manual/occ_apps.html#apps-commands).

See [installation and version selection](INSTALLATION.md), the [release page](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.3) and the [PR verification record](https://github.com/RamonP12/nextcloud-passwords-otp-extension/pull/15).
