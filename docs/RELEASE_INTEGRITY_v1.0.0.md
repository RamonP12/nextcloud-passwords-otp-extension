# Release integrity record — passwords_otp v1.0.0

**Evidence date:** 2026-11-11. **Scope:** preservation and independent verification of the **already published** v1.0.0 source identity and assets; no release asset, tag or release metadata was modified for this record.

## Source and tag identity

| Property | GitHub API observation |
| --- | --- |
| Repository | `RamonP12/nextcloud-passwords-otp-extension` (public) |
| Release | `v1.0.0 - Initial public-source baseline` (published, not a draft, not a prerelease) |
| Release ID | `441672680` |
| Published | `2026-11-11T18:00:06Z` |
| Tag ref | `refs/tags/v1.0.0` |
| Annotated tag object SHA | `1647bc1acaaf6aa2631047cc5996cb55187bca9c` |
| Commit referenced by tag | `56d6de06e4825c9bd03b4b07dec5825d64228390` |
| GitHub tag signature verification | `verified=false`, `reason=unsigned` |
| GitHub release immutability | **`immutable=false`** |

The tag object resolves to the stated source commit, irrespective of subsequent documentation changes on moving `main`. **Do not move, delete or recreate the tag to add documentation or fix an existing ZIP.**

## Published release assets

Asset metadata verified through GitHub's release-by-tag API:

| Asset | GitHub asset ID | Size (bytes) | GitHub SHA256 digest |
| --- | ---: | ---: | --- |
| `passwords_otp-1.0.0.zip` | `735475314` | `242702` | `ffc002d7c41485cac4a4b7eb27659fd5d5dbbd4bd7fd40d78e3ea91373a12256` |
| `passwords_otp-1.0.0.zip.sha256` | `735475330` | `90` | `f7c980a6e0e5a8ae80a3edae5e8fc0b7e4a7e9f479112518f8b1db197a22eec4` |
| `BUILD.json` | `735475331` | `1369` | `bab148c5457d093e3410112888ba493349f4d264f697cf31a5a82ff9c1cca034` |

The operator independently checked the downloaded ZIP against the published SHA256 and compared **all installed files byte-for-byte** to that archive and its build manifest, obtaining `PACKAGE_INTEGRITY_PASS`. The GitHub API asset digest is **metadata reported by GitHub**; it is not a separately provided signature or external timestamp authority.

## Active repository rulesets

Read back from the GitHub Rulesets API on 2026-11-11:

- **Rule 27034743**: `Protect v* release tags - no edits or deletion`, `target=tag`, `enforcement=active`. Ref pattern `refs/tags/v*`; forbids tag updates and deletion; no listed bypass actors.
- **Rule 27051556**: `Protect main - PR only and no force pushes`, `target=branch`, `enforcement=active`. Applies to `refs/heads/main`; rejects deletion/non-fast-forward updates, requires a pull request with squash merging and thread resolution; no listed bypass actors.

These restrictions protect the **tag reference and main branch**. They do **not** themselves protect GitHub release binary attachments from a user who has permission to edit an existing release.

## Important limitation: GitHub release assets are not immutable

The GitHub API reported `immutable=false` for the **already published** release. GitHub's [release immutability documentation](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/prevent-release-changes) specifies that enabling this repository setting is **not retroactive**. The tag ruleset cannot be treated as a substitute for immutable release **assets**.

Therefore the correct claim is **"tag protected and current asset identities/hashes verified"**, **not** "the published v1.0.0 release is immutable". The three recorded digests allow later substitutions to be detected by comparison, but the release attachments still have a mutable administrative surface. No signing or GitHub immutable-release attestation is present for this already-published release.

To make **future** releases immutable, a repository administrator must use Settings → General → Releases → **Enable release immutability** **before publishing the next release**. Use a draft, upload and check all assets, then publish. Do **not** delete and republish v1.0.0 solely to retrofit this setting; that would break the requirement to preserve its published state. No administrative setting was changed as part of this record.

## Read-only verification steps

1. Review [the published release and assets](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.0.0) and its [tag](https://github.com/RamonP12/nextcloud-passwords-otp-extension/tree/v1.0.0).
2. Read GitHub `GET /repos/RamonP12/nextcloud-passwords-otp-extension/git/ref/tags/v1.0.0` and dereference its annotated tag object. Confirm the two SHAs above.
3. Read `GET /repos/RamonP12/nextcloud-passwords-otp-extension/releases/tags/v1.0.0`. Compare asset names, IDs, sizes and SHA256 digest metadata. Inspect `immutable` separately.
4. Download the ZIP and published `.sha256` from the same release; compare the independent expected SHA256 given above. Check the ZIP manifest `BUILD.json` and file digests before installation.
5. Recheck active rulesets `27034743` and `27051556`. Report any mismatch; **do not** move or silently repair the existing v1.0.0 tag.

## Post-release acceptance

The exact published ZIP has since passed a **local** acceptance on Docker Compose / MariaDB / Nextcloud 35.0.2.2 / Passwords 2026.11.20: **10/10 test blocks, 49/49 individual checks**. Details are recorded in [local acceptance report](LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md). A fresh **AIO/PostgreSQL** acceptance of the published ZIP remains pending, and `production_approved=false` remains correct.

The GitHub release description is retained as the **as-published historical snapshot** (it said live installation was still pending at publication). The updated test evidence is kept in versioned project documentation rather than rewriting release assets or metadata.
