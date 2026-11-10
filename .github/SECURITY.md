# Security Policy

## Supported versions

| Version | Status |
| --- | --- |
| 1.0.0 | Current public source baseline; limited compatibility and pilot evidence |
| Earlier internal candidates | Unsupported and not distributed |

## Report vulnerabilities privately

Use the repository's **Private Vulnerability Reporting** feature (Security → Advisories → Report a vulnerability) when enabled. The maintainer must enable this GitHub setting separately; the presence of this policy file does not enable the feature.

Do **not** publish exploit details or security-sensitive findings in a public Issue or Pull Request. If private vulnerability reporting is not enabled, first contact the maintainer using an available private GitHub channel to arrange secure disclosure. Do not assume immediate response times; the project is maintained by a small team.

Include the affected version, impact and reproduction steps using **synthetic** data. Never attach real Passwords exports, OTP setup secrets, passwords, browser cookies, bearer tokens, CSE proofs, or unredacted HTTP requests.

## Security boundaries

The app relies on the original Nextcloud Passwords WebUI API credential. That credential is more privileged than a read-only OTP viewer; browser-side request allowlists cannot enforce a narrower server-side scope. The risk was expressly accepted for the original restricted pilot, not eliminated.

The application also depends on internal Passwords interfaces, and cannot guarantee immediate remote session revocation at browser tab closure. See [Technical security review](../docs/SECURITY_REVIEW.md) for details.

The maintainers will assess reports and coordinate fixes. There is no guaranteed response SLA or general security certification.
