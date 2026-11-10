# Contributing

Thank you for considering a contribution to this unofficial Nextcloud Passwords companion.

## Before contributing

- Search existing Issues and Pull Requests to avoid duplicate work.
- For security issues, follow [.github/SECURITY.md](.github/SECURITY.md); do not disclose them in public Issues.
- For changes affecting authentication, CSE or Passwords API calls, open an Issue to discuss the trust boundary first.
- Do not submit real credentials, TOTP secrets, customer data, private server information, or unredacted browser network logs.

## Development

Use Node.js 22+ and Python 3.10+.

~~~sh
npm ci
npm test
npm run test:client
npm run build
python3 -m unittest discover -s tests/python -v
~~~

For a full local-Nextcloud gate, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). Existing scripts may require a disposable local Nextcloud fixture and desktop Chromium. Do not run the local deployment tool against a public or productive instance.

## Pull requests

1. Branch from the latest main and make a focused change.
2. Keep the original Nextcloud Passwords application and its records unchanged; preserve fail-closed security behavior.
3. Include regression tests for modifications in authentication, OTP parsing, HTTP permissions or deployment.
4. Update user-facing docs and [CHANGELOG.md](CHANGELOG.md) where relevant.
5. Report the precise tests you ran, and distinguish real Nextcloud tests from mocks.
6. Prefer small PRs; maintainers will review security-sensitive changes before merging.

## License and authorship

Contributions are submitted under this project's [AGPL-3.0-or-later](LICENSE) license unless a separate arrangement is agreed. Include notices for newly introduced third-party components.
