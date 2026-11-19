# Development and local verification

Current source version **1.1.1** is the Nextcloud Vue edition. The prior 1.1.0 candidate was locally accepted and superseded by the final wording/version changes. Reproduce the historical public **v1.0.0** only from its pinned tag and matching tooling; the current source and installer reject a 1.0.0 archive.

Work on short feature branches and review changes through pull requests. Preserve the authentication, OTP-window and single-create regression tests. The [migration report](NEXTCLOUD_VUE_MIGRATION.md) records the implementation; [1.1.1 verification](VALIDATION_VUE_1.1.1.md) distinguishes the final checks from the [historical 1.1.0 candidate results](VALIDATION_VUE_1.1.0.md); [VALIDATION.md](VALIDATION.md) remains the historical v1.0.0 record.

## Tooling

- **Node.js 22.12+ in the 22.x line, or 24.x**, matching `package.json`; npm with lockfile v3 support.
- **Python 3.10+** for packaging and installer tests.
- **PHP 8.3–8.5** for standalone controller/security contracts and syntax checks.
- **Chromium/Chrome or Firefox** and Python **Playwright 1.62.0** for the browser suite. Set `CHROME_BIN` if automatic discovery does not locate the desired Chromium executable; Firefox uses the matching Playwright-managed binary.

Install exactly the locked dependencies with `npm ci`; do not run `npm update` as part of routine verification. Vite and Node are build-time dependencies. The packaged Nextcloud app does not need a Node service.

## Local checks without GitHub Actions

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
node --check js/app-111.mjs
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
| Python tests | ZIP/manifest/license gates, AIO scope and rollback, local installer constraints | Synthetic filesystem/backend fixtures; no server deployment |
| PHP tests | Authentication, session binding, CSRF/controller behavior | Standalone framework contracts |
| Compiled browser suite | Actual Vue components, production bundle, pinned client/libsodium, browser WebCrypto, keyboard/dialog/reflow and failure paths | Synthetic HTTPS API responses, shell and clipboard; not an installed Nextcloud server |
| Real Nextcloud integration | PHP routing, shell, CSP/module loading, Passwords API and browser workflows in a disposable server | Applies only to the exact versions/environment and checks recorded in the migration report |

Use synthetic users and OTP seeds. Do not run production installation scripts to satisfy a development test. Narrow viewports and automated accessibility checks do not by themselves prove native browser zoom, screen-reader behavior or complete WCAG conformance.

## Deterministic build and package

`npm run build` compiles Vue Single File Components using pinned Vite and the official `@vitejs/plugin-vue` plugin. The explicit configuration avoids the shared configuration's unused Node/crypto polyfill dependencies. It produces exactly:

- `js/app-111.mjs`
- `css/app-111.css`
- `.build/bundle-modules.json`, a local provenance record for the contributing npm modules and output hashes, production mode, complete source input hashes and allowed build module paths.

The two assets are generated and ignored by Git. Do not edit them manually or include test fixtures in the production entry point. A repeated production build must produce identical JS and CSS bytes; `scripts/local.py --build` performs this comparison in its full source gate.

Package generation requires a clean committed checkout. After committing the reviewed source and confirming that `git status --short` is empty, choose a fresh output directory and run:

```sh
python3 scripts/release.py .build/package
```

Verify the archive from its output directory, because the checksum file names the ZIP relative to that directory:

```sh
cd .build/package
sha256sum -c passwords_otp-1.1.1.zip.sha256
```

The package generator refuses an existing output directory, a dirty checkout, stale asset/module evidence, source/config/lock changes since compilation, changed or missing dependency notices, unsafe paths or an unexpected runtime file. The source commit and clean checkout are rechecked after packaging, before writing output. It records the exact **`source_commit`** and every payload hash in `BUILD.json`, with **`production_approved=false`**. Two package constructions must be identical; that packaging comparison is separate from compiling the frontend twice.

[`scripts/runtime-licenses.json`](../scripts/runtime-licenses.json) pins the reviewed production dependency closure and original notices. Module provenance checks also reject an optional peer that unexpectedly contributes unreviewed code. Read [Third-party notices](../THIRD_PARTY_NOTICES.md) before changing any dependencies; `npm ci` alone is not a license review.

## GitHub Actions status

**GitHub Actions is unavailable because the account/repository quota is exhausted, and repository execution remains disabled.** The retained workflow has **`workflow_dispatch` only**. It has no push or pull-request trigger, so publishing this source or a PR does not request an Actions run.

Do not dispatch the workflow during this migration. Its definition is prepared for later verification after Actions becomes available; it is not evidence that hosted checks ran. Current evidence comes from the local commands and version-bound receipts, and no hosted passing-status badge is asserted.

## Maintainer-only local tools and deployment boundaries

- `scripts/local.py --build` runs locked installation, JS/client tests, audit, Python tests, two production builds and checked packaging for an exact clean commit. Run PHP and browser checks separately as shown above; the build receipt is not a full live-server acceptance.
- `scripts/local.py --preflight`, `--install` and `--verify` target the previously configured **localhost-only MariaDB/PHP 8.5 fixture**. Its historical container names and volume layout are local assumptions. It must not be pointed at an unrelated fixture or changed simply to bypass a mismatch.
- `scripts/deploy.py` is a legacy **localhost test** upgrade/rollback tool. Its supported file/asset mappings include both the 1.1.0 candidate and 1.1.1, but it is not a supported production AIO upgrader.
- `scripts/aio_install.py` supports an explicitly scoped **first install only** and rejects an existing `passwords_otp` app. Current scripts accept only the current 1.1.1 package version. The commands for the published 1.0.0 archive require the 1.0.0 tagged scripts; see [AIO instructions](AIO_MANUAL_INSTALL.md).
- The migration's disposable Nextcloud fixture and its observed results are described separately in the [migration report](NEXTCLOUD_VUE_MIGRATION.md). Do not transfer historical v1.0.0 test totals or database compatibility claims to the current release.

## Release coordination

Update app metadata, package/lock versions, output names, build markers, tests and inventory together. Run the final checks on the final source commit, then bind any candidate archive to that commit. Publishing a source branch or a verification ZIP does not publish a release.

The missing `<bugs>` metadata identified in PR #5 was incorporated narrowly during the 1.1.0 migration and remains in 1.1.1; the separate 1.0.1 branch and published v1.0.0 remain untouched. PR #9's App Store packaging/signing work remains separate. A real certificate, signing verification, publication decisions and an accepted AIO deployment/upgrade path are not supplied by the Vue conversion.
