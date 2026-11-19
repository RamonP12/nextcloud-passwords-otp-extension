# Security Policy

## Supported versions

| Version | Status |
| --- | --- |
| 1.1.1 | Current Nextcloud Vue edition; unsigned, version-specific GitHub distribution with documented local evidence |
| 1.1.0 source candidate | Superseded internal Vue candidate; not published as a separate release |
| 1.0.0 | Published unofficial release; historical, restricted compatibility evidence; tag/assets unchanged |
| Earlier internal candidates | Unsupported; never distributed as public releases |

## Report security vulnerabilities privately

**Report vulnerabilities through [GitHub Private Vulnerability Reporting](https://github.com/RamonP12/nextcloud-passwords-otp-extension/security/advisories/new)** using the repository's **Report a vulnerability** action.

Do **not** disclose vulnerability details in public GitHub issues, discussions, or pull requests. No alternative confidential reporting channel is advertised. The maintainer will triage incoming private reports and coordinate disclosure where possible.

Include the affected version and source commit, impact and reproduction steps using **synthetic** data. Never attach real Passwords exports, OTP setup secrets, passwords, cookies, bearer tokens, CSE proofs or unredacted HTTP requests.

## Security boundaries

The app relies on the original Nextcloud Passwords WebUI bearer token. That token has more privileges than the OTP viewer's UI; browser-side request allowlists cannot create a server-enforced least-privilege credential. This architectural limitation remains openly tracked in [issue #1](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1).

The Vue migration preserves this limitation and does not create a server-enforced least-privilege token. Current evidence is recorded in [1.1.1 verification](../docs/VALIDATION_VUE_1.1.1.md), with the [historical 1.1.0 candidate results](../docs/VALIDATION_VUE_1.1.0.md) kept separate. Historical v1.0.0 test totals are not current-source results.

The app also depends on internal Passwords integration interfaces and cannot guarantee immediate remote token revocation when a browser tab closes. See the [technical security review](../docs/SECURITY_REVIEW.md).

Current distribution remains unsigned and version-specific. The first-install AIO tool does not upgrade existing OTP installations, and independent App Store signing work is not a release approval. GitHub Actions is unavailable; a workflow definition is not evidence of hosted verification.

The maintainer will assess and coordinate reports where possible. There is no guaranteed response time, security certification, or general production approval.
