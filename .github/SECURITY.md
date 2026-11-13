# Security Policy

## Supported versions

| Version | Status |
| --- | --- |
| 1.0.0 | Current unofficial source/release baseline; restricted compatibility evidence |
| Earlier internal candidates | Unsupported; never distributed as public releases |

## Report security vulnerabilities privately

**Report vulnerabilities through [GitHub Private Vulnerability Reporting](https://github.com/RamonP12/nextcloud-passwords-otp-extension/security/advisories/new)** using the repository's **Report a vulnerability** action.

Do **not** disclose vulnerability details in public GitHub issues, discussions, or pull requests. No alternative confidential reporting channel is advertised. The maintainer will triage incoming private reports and coordinate disclosure where possible.

Include the affected version, impact and reproduction steps using **synthetic** data. Never attach real Passwords exports, OTP setup secrets, passwords, cookies, bearer tokens, CSE proofs or unredacted HTTP requests.

## Security boundaries

The app relies on the original Nextcloud Passwords WebUI bearer token. That token has more privileges than the OTP viewer's UI; browser-side request allowlists cannot create a server-enforced least-privilege credential. This architectural limitation remains openly tracked in [issue #1](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1).

The app also depends on internal Passwords integration interfaces and cannot guarantee immediate remote token revocation when a browser tab closes. See the [technical security review](../docs/SECURITY_REVIEW.md).

The maintainer will assess and coordinate reports where possible. There is no guaranteed response time, security certification, or general production approval.
