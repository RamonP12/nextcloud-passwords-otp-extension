# Pre-publication checklist for v1.0.0

This checklist covers **repository administration only**. The verified v1.0.0 ZIP and tag are immutable: do **not** move `v1.0.0`, edit the archive or rebuild its release assets.

## Publication order

1. Review the GitHub profile in an **unauthenticated** browser to ensure the displayed name, profile links and contact fields do not reveal unwanted identity. The corrected tag uses the pseudonym and a GitHub noreply address.
2. Ensure the **new clean repository** is private and that the two historical repositories remain private and archived. The old sensitive tag object must yield 404 **in the clean repository**.
3. In the clean repository Settings, switch **visibility to Public**. This change exposes the current source history and published metadata immediately.
4. **Immediately** enable **Private Vulnerability Reporting** at Security and quality → Advanced Security/Advisories. Confirm that **Report a vulnerability** appears for an unauthenticated visitor. No other confidential channel is advertised.
5. Enable **Dependency graph**, **Dependabot alerts**, **Dependabot security updates**, **Secret scanning** and **Push protection** (where offered) in Settings → Advanced Security. These are settings, not enabled by merely adding `.github/dependabot.yml`. Regular Dependabot **version-update** PRs remain paused by `open-pull-requests-limit: 0`; security updates are separate.
6. Update the existing **draft** release with [these notes](RELEASE_NOTES_v1.0.0.md) from a checkout of the current `main`:

   ```sh
   gh release edit v1.0.0 \
     --repo RamonP12/nextcloud-passwords-otp-extension \
     --notes-file docs/RELEASE_NOTES_v1.0.0.md
   gh release view v1.0.0 \
     --repo RamonP12/nextcloud-passwords-otp-extension \
     --json isDraft,tagName,assets
   ```

7. After reviewing the release preview and asset SHA256, **publish** the draft:

   ```sh
   gh release edit v1.0.0 \
     --repo RamonP12/nextcloud-passwords-otp-extension \
     --draft=false
   ```

8. Set up GitHub **rulesets** for branch `main` (restrict deletion/force pushes; require PRs when workflow is operational) and tags matching `v*` (restrict updates and deletions). **Do not require green CI checks while GitHub Actions are disabled**, or every PR will be blocked. Enable and verify CI deliberately before requiring named checks. Select no unnecessary bypass actors.
9. Under Repository Settings, optionally disable unused **Projects**, permit only **Squash merge**, and enable **Automatically delete head branches**.
10. Set repository topics: `nextcloud`, `nextcloud-app`, `totp`, `otp`, `2fa`, `passwords`.
11. Confirm as an unauthenticated visitor that the release assets download, the issue and security reporting are accessible, `main` and the tagged sources contain no private contact details, and the old quarantine remains private.

## Invariants

- Release source commit: `56d6de06e4825c9bd03b4b07dec5825d64228390`.
- Release ZIP SHA256: `ffc002d7c41485cac4a4b7eb27659fd5d5dbbd4bd7fd40d78e3ea91373a12256`.
- The new untagged `main` documentation commits do **not** change the tested release; `v1.0.0` remains immutable.
- All GitHub Actions checks are **currently disabled**, and the latest published v1.0.0 package has **not** passed a documented real first-install verification.
- If any admin control cannot be activated, stop and report the gap rather than claiming it is enabled.
