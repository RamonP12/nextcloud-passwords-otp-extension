# Development and local tests

The public project starts at **v1.0.0**. Work from main, use short feature branches and Pull Requests, and keep regression tests for authentication and OTP logic.

## Tooling

Node.js 22+, npm, Python 3.10+, and PHP for standalone security-contract tests.

~~~sh
npm ci
npm test
npm run test:client
npm run test:php
python3 -m unittest discover -s tests/python -v
npm audit
npm run build
python3 scripts/release.py .build/package
~~~

The package generator requires a clean Git checkout and commits an immutable **source_commit** to BUILD.json. The built bundle (js/app-100.js) is generated; it is intentionally absent from Git and should not be hand-edited.

## Maintainer-only legacy and local test tools

- `scripts/local.py --build` is the maintainer's comprehensive local preflight wrapper. Its `--preflight`, `--install` and `--verify` modes depend on a separately configured, disposable **localhost-only Nextcloud fixture**. Container names, image names and volume layout in this tool are local test assumptions, **not** a reproducible public setup guide.
- `scripts/deploy.py` is a **legacy internal upgrade/rollback test tool**, including older 0.x pilot-version scenarios. It is not a supported public production upgrader or a required step for installation of v1.0.0.
- The public, explicitly gated **first-time AIO** installer is `scripts/aio_install.py`. Its instructions are in [AIO manual installation](AIO_MANUAL_INSTALL.md).
- The exact local Nextcloud fixture and browser integrations have not been packaged into a self-contained public test environment. **A real local browser acceptance of the official ZIP was subsequently performed on 2026-11-11 (49/49 checks)**; this is distinct from mocked/local-fixture unit tests and is documented in [local acceptance](LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md). The successful localhost test does not establish support for arbitrary external installations.

**Never run a destructive script against production to satisfy a test gate.** Use dummy accounts and synthetic OTP seeds; distinguish unit tests, synthetic browser tests and live environment checks.

The GitHub Actions workflow is present but **repository-level Actions execution is intentionally disabled** at this stage; no hosted green CI check can currently be asserted or used as a required branch rule. Automating PR merging must await CI activation and one successful workflow run.

## Release process

Update appinfo/info.xml, package.json, package-lock.json, the asset names and tests consistently; run the full gate on the final commit. Keep release archives bound to that final commit and publish SHA256 and third-party notices. Version 1.0.0 does **not** provide an in-place production upgrade for existing OTP installations. **Automated release checks and real localhost installation of the exact ZIP passed; the first-install test on AIO/PostgreSQL is still pending.** Reproduce this binary only from tag `v1.0.0`, never from moving `main`. See [validation](VALIDATION.md) and [release integrity](RELEASE_INTEGRITY_v1.0.0.md).
