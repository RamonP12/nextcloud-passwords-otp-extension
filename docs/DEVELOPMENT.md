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

## Optional complete local fixture

scripts/local.py --build and --preflight run extra checks (including isolated Chromium, PHP and a local Nextcloud fixture). --install and --verify affect only the developer's specifically configured **localhost test instance** and are not suitable for the production AIO server.

**Never run a destructive script against production to satisfy a test gate.** Use dummy accounts and synthetic OTP seeds, and report exactly which real and mocked tests ran.

## Release process

Update appinfo/info.xml, package.json, package-lock.json, the asset names and tests consistently; run the full gate on the final commit. Keep release archives bound to that final commit and publish SHA256 and third-party notices. Version 1.0.0 does **not** provide an in-place production upgrade for existing OTP installations.
