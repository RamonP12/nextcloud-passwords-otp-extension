# Security Policy

## Supported versions

| Version | Status |
| --- | --- |
| 1.0.0 | Current unofficial source/release baseline; restricted compatibility evidence |
| Earlier internal candidates | Unsupported; never distributed as public releases |

## Report security vulnerabilities privately

**Use [GitHub Private Vulnerability Reporting](https://github.com/RamonP12/nextcloud-passwords-otp-extension/security/advisories/new)** after it is explicitly enabled for this repository (**Security and quality → Advisories → Report a vulnerability**). The maintainer must activate the feature **immediately after making the repository public**; this file does not enable it.

**No alternative confidential reporting channel is currently configured.** GitHub does **not** provide direct messages between arbitrary users, and this project does not advertise a dedicated security mailbox. Do not assume that an unspecified “private GitHub channel” exists.

If the private-reporting option is not available, **do not publish any vulnerability details**. You may open a minimal, non-sensitive Issue requesting that Private Vulnerability Reporting be enabled; omit exploit details, affected credentials, private infrastructure and proof-of-concept material. Wait for a confirmed confidential channel before sending sensitive content.

When reporting, include the affected version, impact and reproduction steps using **synthetic** data. Never attach real Passwords exports, OTP setup secrets, passwords, cookies, bearer tokens, CSE proofs or unredacted HTTP requests.

## Security boundaries

The app relies on the original Nextcloud Passwords WebUI bearer token. That token has more privileges than the OTP viewer's UI; browser-side request allowlists cannot create a server-enforced least-privilege credential. This architectural limitation remains openly tracked in [issue #1](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1).

The app also depends on internal Passwords integration interfaces and cannot guarantee immediate remote token revocation when a browser tab closes. See the [technical security review](../docs/SECURITY_REVIEW.md).

The maintainer will assess and coordinate reports where possible. There is no guaranteed response time, security certification, or general production approval.
