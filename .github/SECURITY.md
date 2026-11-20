# Security Policy

## Supported versions

| Version | Status |
| --- | --- |
| 1.1.4 | Current GitHub release with localhost and single-installation AIO acceptance. [Version-specific verification](../docs/VALIDATION_1.1.4.md) |
| 1.1.3 | Historical GitHub release. Unsigned TAR/ZIP, verified localhost upgrade and OTP functions. See the [verification record](../docs/VALIDATION_1.1.3.md) for the acceptance limits. |
| 1.1.2 | Historical Vue release with documented Passwords prerequisite and localhost lifecycle checks |
| 1.1.1 | Historical Vue release; superseded, tag and assets unchanged |
| 1.1.0 source candidate | Superseded internal Vue candidate; not published as a separate release |
| 1.0.0 | Published unofficial release; historical, restricted compatibility evidence; tag/assets unchanged |
| Earlier internal candidates | Unsupported; never distributed as public releases |

## Report security vulnerabilities privately

**Report vulnerabilities through [GitHub Private Vulnerability Reporting](https://github.com/RamonP12/nextcloud-passwords-otp-extension/security/advisories/new)** using the repository's **Report a vulnerability** action.

Do **not** disclose vulnerability details in public GitHub issues, discussions, or pull requests. No alternative confidential reporting channel is advertised. The maintainer will triage incoming private reports and coordinate disclosure where possible.

Include the affected version and source commit, impact and reproduction steps using **synthetic** data. Never attach real Passwords exports, OTP setup secrets, passwords, cookies, bearer tokens, CSE proofs or unredacted HTTP requests.

## Security boundaries

The app relies on the original Nextcloud Passwords WebUI bearer token. That token has more privileges than the OTP viewer's UI; browser-side request allowlists cannot create a server-enforced least-privilege credential. This architectural limitation remains openly tracked in [issue #1](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1).

The Vue migration preserves this limitation and does not create a server-enforced least-privilege token. Current evidence is recorded in the [1.1.4 release](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.4). The [1.1.3 verification record](../docs/VALIDATION_1.1.3.md) covers that version. The [1.1.2 verification](../docs/VALIDATION_1.1.2.md) and [local lifecycle acceptance](../docs/LOCAL_ACCEPTANCE_v1.1.2_2026-11-19.md) are version-specific, as are [historical 1.1.1 verification](../docs/VALIDATION_VUE_1.1.1.md) and the [historical 1.1.0 candidate results](../docs/VALIDATION_VUE_1.1.0.md). Historical v1.0.0 test totals are not current-source results.

The app also depends on internal Passwords integration interfaces and cannot guarantee immediate remote token revocation when a browser tab closes. Version 1.1.4 validates Passwords on OTP requests and preserves the configured activation scope when Passwords is unavailable. The integration still uses private Passwords interfaces. The [dependency lifecycle](../docs/DEPENDENCY_LIFECYCLE.md) distinguishes global dependency loss from per-user group denial and documents fallback detection timing. See the [technical security review](../docs/SECURITY_REVIEW.md).

Current distribution remains unsigned and version-specific. The first-install AIO tool does not upgrade existing OTP installations, and the prepared App Store signing workflow is not a release approval. The release notes and linked verification records describe the local checks. [Development](../docs/DEVELOPMENT.md#github-actions) documents the enabled CI workflow.

The maintainer will assess and coordinate reports where possible. There is no guaranteed response time, security certification, or general production approval.
