# Development and local verification

Published **1.1.3** adds branding and direct code copying. The [release and verification record](VALIDATION_1.1.3.md) binds the package and acceptance evidence to their source revisions. Published **1.1.2** added enforced Passwords prerequisites and deterministic tar.gz distribution to the Nextcloud Vue edition. The prior five-point 1.1.0 localhost acceptance alone did not verify the new lifecycle changes; a subsequent [1.1.2 localhost report](LOCAL_ACCEPTANCE_v1.1.2_2026-11-19.md) records successful upgrade and normal disable/reenable checks. Negative and destructive lifecycle paths still require separate testing. Reproduce the historical public **v1.0.0** only from its pinned tag and matching tooling; the current source and installer reject a 1.0.0 archive.

Work on short feature branches and review changes through pull requests. Preserve the authentication, OTP-window and single-create regression tests. See the [1.1.3 verification record](VALIDATION_1.1.3.md) for the current release and [dependency lifecycle](DEPENDENCY_LIFECYCLE.md) for the prerequisite logic. The [1.1.2 verification record](VALIDATION_1.1.2.md) covers that version. The [migration report](NEXTCLOUD_VUE_MIGRATION.md) records the original implementation. [Historical 1.1.1 verification](VALIDATION_VUE_1.1.1.md) distinguishes the final checks from the [historical 1.1.0 candidate results](VALIDATION_VUE_1.1.0.md). [VALIDATION.md](VALIDATION.md) remains the historical v1.0.0 record.

## Tooling

- **Node.js 22.12+ in the 22.x line, or 24.x**, matching `package.json`; npm with lockfile v3 support.
- **Python 3.10+** for packaging and installer tests.
- **PHP 8.3–8.5** for standalone controller/security contracts and syntax checks.
- **Chromium/Chrome or Firefox** and Python **Playwright 1.62.0** for the browser suite. Set `CHROME_BIN` if automatic discovery does not locate the desired Chromium executable; Firefox uses the matching Playwright-managed binary.

Install exactly the locked dependencies with `npm ci`; do not run `npm update` as part of routine verification. Vite and Node are build-time dependencies. The packaged Nextcloud app does not need a Node service.

## Local checks

Run these commands in the repository root:

```sh
npm ci --no-audit --no-fund
npm test
npm run test:client
python3 -m unittest discover -s tests/python -v
npm run test:php
git ls-files -z -- '*.php' | xargs -0 -n1 php -l
npm audit --audit-level=low
npm run build
node --check js/app-120-dev.mjs
```

The browser suite needs the **fresh production build** from the preceding step. A separate Python environment can be prepared as follows:

```sh
python3 -m venv .build/browser-venv
.build/browser-venv/bin/python -m pip install playwright==1.62.0
.build/browser-venv/bin/python tests/browser/desktop.py --output .build/browser
```

If Playwright is already available to `python3`, `npm run test:browser` runs the same suite. Its driver discovers `chromium-headless-shell`, `chromium` or `google-chrome`, or uses `CHROME_BIN`. The browser itself must be installed; the test driver does not silently install one.

To check the same production-bundle suite in Firefox, install the matching browser explicitly and select it:

```sh
.build/browser-venv/bin/python -m playwright install firefox
.build/browser-venv/bin/python tests/browser/desktop.py --browser firefox --output .build/browser-firefox
```

The desktop suite includes the six additional lifecycle regressions in `tests/browser/lifecycle.py` and verifies that JS/CSS do not change during the run. For the installed-server layer, follow [the real Nextcloud integration instructions](../tests/integration/README.md); it requires a disposable HTTPS fixture and private test credentials.

### What each layer demonstrates

| Layer | Checks | Boundary |
| --- | --- | --- |
| JavaScript unit tests | Parser/crypto, transport, domain session/create, DOM-free presenter and application lifecycle | Unit fixtures/injected clocks and clients |
| `test:client` | Actual pinned Passwords client and libsodium integration | Synthetic upstream responses |
| Python tests | ZIP/TAR/manifest/license gates, hostile archives, real cryptographic checks with temporary test certificates, AIO scope and rollback | Synthetic filesystem/backend fixtures; temporary certificates are not Nextcloud-issued |
| PHP tests | Authentication, session binding, CSRF/controller behavior and Passwords dependency transitions | Standalone framework contracts; actual installed-server lifecycle acceptance is separate |
| Compiled browser suite | Actual Vue components, production bundle, pinned client/libsodium, browser WebCrypto, keyboard/dialog/reflow and failure paths | Synthetic HTTPS API responses, shell and clipboard; not an installed Nextcloud server |
| Real Nextcloud integration | PHP routing, shell, CSP/module loading, Passwords API and browser workflows in a disposable server | Applies only to the exact versions/environment and checks recorded in the migration report |

Use synthetic users and OTP seeds. Do not run production installation scripts to satisfy a development test. Narrow viewports and automated accessibility checks do not by themselves prove native browser zoom, screen-reader behavior or complete WCAG conformance.

## Deterministic build and package

`npm run build` compiles Vue Single File Components into `.build/vite/` using pinned Vite and the official `@vitejs/plugin-vue` plugin. The build checks the output before copying assets to the paths Nextcloud serves. It exposes these files:

- `js/app-120-dev.mjs`
- `css/app-120-dev.css`
- `.build/bundle-modules.json`, a local provenance record for the contributing npm modules and output hashes, production mode, complete source input hashes and allowed build module paths.

The JS module includes libsodium even for vaults without client-side encryption. The pinned Passwords client's default class loader imports it for the master-password challenge, keychains and encryption. At the time of review the module was about 1.10 MB (368 kB gzip). A lazy split requires testing the challenge and CSE paths as well as extending the fixed asset inventory, Nextcloud module delivery and archive verification.

The two assets are generated and ignored by Git. Do not edit them manually or include test fixtures in the production entry point. A repeated production build must produce identical JS and CSS bytes; `scripts/local.py --build` performs this comparison in its full source gate.

Package generation requires a clean committed checkout. After committing the reviewed source and confirming that `git status --short` is empty, choose a fresh output directory and run:

```sh
python3 scripts/release.py .build/package
```

Verify both archives from their output directory; the checksum files use relative filenames:

```sh
cd .build/package
sha256sum -c passwords_otp-1.2.0-dev.zip.sha256
sha256sum -c passwords_otp-1.2.0-dev.tar.gz.sha256
```

The package generator refuses an existing output directory, a dirty checkout, stale asset/module evidence, source/config/lock changes since compilation, changed or missing dependency notices, unsafe paths or an unexpected runtime file. The source commit and clean checkout are rechecked after packaging, before writing output. It records the exact **`source_commit`** and every payload hash in `BUILD.json`, with **`production_approved=false`**. Two constructions of each archive must be identical; that comparison is separate from compiling the frontend twice. Both archives have exactly one `passwords_otp/` root and identical runtime payloads. The ordinary artifacts are unsigned. The separate [App Store signing procedure](APPSTORE_PACKAGING.md) requires real certificate trust verification and an archive signature.

[`scripts/runtime-licenses.json`](../scripts/runtime-licenses.json) pins the reviewed production dependency closure and original notices. Module provenance checks also reject an optional peer that unexpectedly contributes unreviewed code. Read [Third-party notices](../THIRD_PARTY_NOTICES.md) before changing any dependencies; `npm ci` alone is not a license review.

## Compare a rebuild with a release

The SHA-256 checksums attached to a GitHub release identify its exact ZIP and
TAR.GZ bytes. Use those checksums when verifying the downloaded release for
installation. For a source rebuild on a different host, compare the verified
file inventory and uncompressed bytes, including `BUILD.json`. A matching
manifest is useful only after verifying the archive entries against its hashes.

Run the comparison below from the exact release tag after a successful clean
`python3 scripts/local.py --build`. Download both published archives, their
checksum files and `BUILD.json` into the same directory.

```sh
published_dir="$PWD/.build/published"
rebuilt_dir="$PWD/.build/$(git rev-parse HEAD)/package"
python3 - "$published_dir" "$rebuilt_dir" <<'PYTHON'
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path("scripts").resolve()))
from release import VERSION, digest, validate_package
from appstore_package import verify_tar

def read_checked(directory, suffix):
    path = directory / f"passwords_otp-{VERSION}.{suffix}"
    expected = path.with_name(path.name + ".sha256").read_text().split()[0]
    data = path.read_bytes()
    if digest(data) != expected:
        raise SystemExit(f"SHA-256 mismatch: {path}")
    return data, expected

def verified_files(directory):
    archive, expected = read_checked(directory, "zip")
    files, _ = validate_package(archive, expected)
    if (directory / "BUILD.json").read_bytes() != files["BUILD.json"]:
        raise SystemExit(f"Attached BUILD.json differs from the ZIP: {directory}")
    tar, _ = read_checked(directory, "tar.gz")
    verify_tar(tar, files)
    return files

published, rebuilt = (verified_files(pathlib.Path(path)) for path in sys.argv[1:])
differences = sorted(name for name in published.keys() | rebuilt.keys()
                     if published.get(name) != rebuilt.get(name))
if differences:
    raise SystemExit("Different package files: " + ", ".join(differences))
print(f"Content matches: {len(published) - 1} payload files and BUILD.json in both formats")
PYTHON
```

For byte-identical reproduction of v1.1.3 the tested reference toolchain was
**Node.js 24.22.3, npm 11.19.1, CPython 3.12.14 and classic zlib 1.3.2**.
Fresh builds from v1.1.2 and v1.1.3 reproduced their published checksums. Record the
compression library actually used by Python when diagnosing a difference:

```sh
python3 -c 'import sys, zlib; print(sys.version); print("zlib build:", zlib.ZLIB_VERSION, "runtime:", zlib.ZLIB_RUNTIME_VERSION, "zlib-ng:", getattr(zlib, "ZLIBNG_VERSION", "not reported"))'
```

Python exposes `ZLIBNG_VERSION` starting with 3.14 when built against zlib-ng.
For older or distribution-patched interpreters, also consult their package
metadata or shared-library linkage. The compressed size alone cannot identify
the compressor. [Python zlib documentation](https://docs.python.org/3/library/zlib.html)

### Controlled comparison for Issue #16

The tagged packer on CPython 3.12.14 with classic zlib 1.3.2 reassembled the
verified v1.1.2 and v1.1.3 payloads to exactly the published ZIP and TAR.GZ
bytes. In a second run, only the compressor bound to `zipfile` and `gzip`
was switched to zlib-ng 2.3.3 in the same process. Both tags produced the
same pattern:

- All 17 payload files and `BUILD.json` matched byte for byte. ZIP entry
  order, timestamps, permissions, compression method and CRCs matched.
- The raw DEFLATE streams changed for exactly five ZIP entries. Those were
  the JavaScript, CSS, `LICENSE`, `THIRD_PARTY_LICENSES.txt` and
  `THIRD_PARTY_NOTICES.md`. For v1.1.3 the ZIP grew from 598,254 to 600,847 bytes.
- The uncompressed TAR, gzip header and gzip trailer matched byte for byte.
  The v1.1.3 TAR.GZ grew from 594,430 to 597,217 bytes.

The cross-environment compression difference is covered by the documented
content check. A digest-pinned build image could standardize future
release-byte reproduction if required. [Issue #16](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/16)

## GitHub Actions

The verification workflow uses standard GitHub-hosted Ubuntu runners with read-only repository permissions. Pull requests targeting `main`, pushes to `main` and manual dispatch trigger it. GitHub provides standard runner usage free for public repositories. [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

Report the result of the actual workflow run for the tested commit. The hosted artifact is an unsigned verification package. Live Nextcloud and AIO acceptance are separate checks. Routine Dependabot version-update PRs are paused by the zero limits in [Dependabot configuration](../.github/dependabot.yml). Security alerts and security-update PRs use separate repository settings.

### Verification on 2026-11-20

[PR #25](https://github.com/RamonP12/nextcloud-passwords-otp-extension/pull/25) restored the push and pull request triggers. The first push run exposed a timing issue in the browser test for vault inactivity. [PR #26](https://github.com/RamonP12/nextcloud-passwords-otp-extension/pull/26) let the dialog initialize its focus trap before jumping the test clock. The test still checks that inactivity locks the vault and clears the inputs without sending a Passwords keepalive.

| Scope | Result |
| --- | --- |
| Hosted package and PHP checks on commit `5865b351351da249e830ced415c1047b3fe71621` | 249 JavaScript, 20 pinned-client and 103 Python tests passed. PHP 8.5.13 lint, 87 security assertions and 20 dependency assertions passed. npm audit reported zero vulnerabilities for the checked lockfile. Both bundle builds, verified ZIP/TAR generation and artifact upload passed. |
| Hosted Chromium on the same commit | All 44 cases passed with the production bundle and synthetic shell, API and clipboard. The delayed session check confirmed that returning to the window shows a waiting message and copy requires a fresh click. |
| Local build on commit `010939c9aec9129bafff86ea97905e3758762a50` | Node 22.22.2 passed the full build and package gate on the first maintenance merge. |
| Local integration on the PR #25 source tree | PHP 8.4.27 passed the standalone contracts and all 20 pinned Nextcloud 35.0.2 lifecycle component cases with service doubles. |

[Successful PR run](https://github.com/RamonP12/nextcloud-passwords-otp-extension/actions/runs/44737110666) and [successful push run on `main`](https://github.com/RamonP12/nextcloud-passwords-otp-extension/actions/runs/44737362435).

## Maintainer-only local tools and deployment boundaries

The reviewed Passwords build for installer checks is declared in
[`PasswordsDependency.php`](../lib/Service/PasswordsDependency.php).
The app derives its runtime patch range from that build and still checks
installed metadata and upstream interfaces. The Python installers check the
exact reviewed build. The AIO development installer reads the policy from the
SHA-verified package when available. A standalone development `--inspect`
needs the matching ZIP and `--sha256` when it runs outside a source checkout.

- `scripts/local.py --build` runs locked installation, JS/client tests, audit, Python tests, two production builds and checked packaging for an exact clean commit. Run PHP and browser checks separately as shown above; the build receipt is not a full live-server acceptance.
- `scripts/local.py --preflight`, `--install` and `--verify` target the previously configured **localhost-only MariaDB/PHP 8.5 fixture**. Its historical container names and volume layout are local assumptions. It must not be pointed at an unrelated fixture or changed simply to bypass a mismatch.
- `scripts/deploy.py` is a legacy **localhost test** upgrade/rollback tool. Its supported file/asset mappings include the 1.1.0 candidate, 1.1.1, 1.1.2 and 1.1.3, but it is not a supported production AIO upgrader. The new dependency migration/job state must be accounted for in rollback; consult its version-specific validation record.
- `scripts/aio_install.py` supports an explicitly scoped **first install only** and rejects an existing `passwords_otp` app. Use the package and installer scripts from the same version. Use the matching v1.1.3 tag with the published archive. See the [AIO instructions](AIO_MANUAL_INSTALL.md).
- The migration's disposable Nextcloud fixture and its observed results are described separately in the [migration report](NEXTCLOUD_VUE_MIGRATION.md). Do not transfer historical v1.0.0 test totals or database compatibility claims to the current release.

## Release coordination

Development builds on `main` use **1.2.0-dev**. After tagging a stable release, immediately advance `main` to the next development version and include the suffix in the asset basename. Update app metadata, package/lock versions, output names, build markers, tests and inventory together. The next stable version sorts after its development version in Nextcloud. [Nextcloud release process](https://docs.nextcloud.com/server/stable/developer_manual/app_publishing_maintenance/release_process.html) Run the final checks on the final source commit, then bind any candidate archive to that commit. Publishing a source branch or a verification ZIP does not publish a release.

The superseded `release/v1.0.1-appinfo-schema` branch was deleted on 2026-11-20. The candidate commit is still accessible through [PR #5](https://github.com/RamonP12/nextcloud-passwords-otp-extension/pull/5) and the resolved metadata change is in the published Vue line. See [issue #2](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/2).

Version 1.1.2 incorporates reviewed TAR/signing preparation and corrects the signature-path assumption in draft PR #9. v1.1.3 is distributed through GitHub as an unsigned release. Track App Store publication in [#14](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/14). AIO/PostgreSQL acceptance and dependency lifecycle checks on the maintainer's localhost remain distinct from synthetic contract tests.
