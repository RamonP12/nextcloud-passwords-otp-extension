# Contributing

Contributions target an unofficial Nextcloud Passwords companion. **1.1.3** is the current published Vue release. Historical release and verification records are available for earlier versions. Do not alter existing release tags, assets or recorded checksums.

## Before contributing

- Search existing issues and pull requests to avoid duplicate work.
- Follow [.github/SECURITY.md](.github/SECURITY.md) for vulnerabilities; do not disclose them in public issues.
- Discuss changes to authentication, CSE or Passwords API permissions with the maintainer and preserve the documented trust boundary.
- Use synthetic data. Do not submit real credentials, OTP seeds, customer records, private server details or unredacted browser/network logs.

## Local development

Use **Node.js 22.12+ in the 22.x line or 24.x**, Python 3.10+, and PHP for the security contracts. Browser checks require Chromium/Chrome and Python Playwright. Install the exact npm lockfile:

```sh
npm ci --no-audit --no-fund
npm test
npm run test:client
python3 -m unittest discover -s tests/python -v
npm run test:php
npm audit --audit-level=low
npm run build
npm run test:browser
```

See [Development](docs/DEVELOPMENT.md) for the isolated Playwright environment, syntax checks, deterministic build and version-matched packaging. Compile before running the browser suite: it loads the actual production Vue bundle, rather than substituting runtime modules.

**GitHub Actions quota is exhausted and execution is disabled.** The workflow has only a future manual `workflow_dispatch` trigger; pushes and PRs do not request Actions runs. Do not dispatch it or claim a hosted passing status during this migration. Report local checks with their exact scope and source version.

Real Nextcloud integration is separate from synthetic unit/browser tests. See [1.1.3 verification](docs/VALIDATION_1.1.3.md), [1.1.2 verification](docs/VALIDATION_1.1.2.md), [dependency lifecycle](docs/DEPENDENCY_LIFECYCLE.md), [historical 1.1.1 verification](docs/VALIDATION_VUE_1.1.1.md), the [migration report](docs/NEXTCLOUD_VUE_MIGRATION.md) and [historical candidate validation](docs/VALIDATION_VUE_1.1.0.md) for each fixture and its evidence. The legacy localhost deployment tools depend on a specific previous fixture and are not production installers or general upgrade tools.

## Pull requests

1. Branch from the latest appropriate source base and keep the change focused.
2. Preserve the original Passwords application, the domain authentication/encryption logic and fail-closed behavior. Creating a record must remain a deliberate, guarded user action.
3. Retain meaningful regression coverage for session timing, stale async results, clipboard validity, form clearing, API permissions and deployment boundaries when those areas change.
4. Update user-facing documentation and [CHANGELOG.md](CHANGELOG.md).
5. State which tests actually ran. Distinguish unit fixtures, the compiled synthetic browser suite, real Nextcloud integration and AIO/PostgreSQL acceptance.
6. Review source and dependencies before packaging from a clean commit. Generated JS/CSS must correspond to the current source/config/lock hashes; rebuild after changing those inputs.

Changing the supported Passwords versions requires a new integration review; an install prerequisite does not make private upstream APIs stable. Preserve per-user denial versus global dependency failure, installation failure propagation, configured activation scope and rollback bookkeeping. Never replace a missing real signing certificate with a self-signed release certificate.

Changing npm dependencies requires reviewing [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), the locked runtime/license inventory and actual bundled module inputs. Do not bypass an inventory, source-freshness or vulnerability gate to make a build pass.

## License and authorship

Contributions are submitted under this project's [AGPL-3.0-or-later](LICENSE) license unless a separate arrangement is agreed. Preserve original notices and attribution for third-party components.
