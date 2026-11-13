# v1.0.0 publication record (historical)

> **Publication completed on 2026-11-11.** This is a record, not a runbook to execute again. Never re-publish, retag or replace the verified v1.0.0 assets.

## Published baseline

- Public repository: [RamonP12/nextcloud-passwords-otp-extension](https://github.com/RamonP12/nextcloud-passwords-otp-extension)
- Published release: [v1.0.0](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.0.0)
- Release source commit: `56d6de06e4825c9bd03b4b07dec5825d64228390`
- Release ZIP SHA256: `ffc002d7c41485cac4a4b7eb27659fd5d5dbbd4bd7fd40d78e3ea91373a12256`
- The `v*` tags and `main` are protected by active repository rulesets.
- **v1.0.0 release attachments are not immutable**: GitHub reported `immutable=false`. Enabling release immutability later only affects future releases; see [release integrity record](RELEASE_INTEGRITY_v1.0.0.md) and [issue #3](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/3).

## Security and acceptance

- Vulnerability reports belong in [GitHub Private Vulnerability Reporting](../.github/SECURITY.md). The feature is configured in repository settings, not by the policy file itself.
- Dependency scanning/alerts and security updates are separate GitHub repository settings. The [Dependabot configuration](../.github/dependabot.yml) currently pauses routine version-update PRs while CI is disabled.
- The exact published v1.0.0 ZIP passed local Nextcloud 35 / MariaDB acceptance: **10/10 blocks, 49/49 checks**. See [local acceptance](LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md) and [validation](VALIDATION.md).
- A fresh AIO/PostgreSQL first-install acceptance remains open; `production_approved=false`.
- GitHub Actions has no recorded runs while disabled. Do not require a green CI check until workflows are enabled and a named check is observed.

## Future releases

Before publishing a future version, enable release immutability, complete the version-specific validation and integrity checks, upload and verify assets in a draft, and publish only after release gates pass. Preserve the historical v1.0.0 tag and assets unchanged.

For the full historical integrity evidence and read-only verification steps, refer to [RELEASE_INTEGRITY_v1.0.0.md](RELEASE_INTEGRITY_v1.0.0.md).
