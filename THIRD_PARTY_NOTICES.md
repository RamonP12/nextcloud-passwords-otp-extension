# Third-party components and licensing

This project's own source is **AGPL-3.0-or-later**. Third-party components retain their original licenses. The **1.1.0 Vue migration candidate** uses the exact versions and tarball integrity values in `package-lock.json`; it does not change the published v1.0.0 distribution.

| Component | Locked version | Declared license | Use |
| --- | --- | --- | --- |
| @nextcloud/vue | 9.14.1 | AGPL-3.0-or-later | Nextcloud UI components; component subpath imports |
| vue | 3.5.45 | MIT | Vue runtime and its exact-version runtime packages |
| passwords-client | 1.0.0-beta.6117 | ISC | Existing Passwords client and encryption integration |
| libsodium-wrappers-sumo / libsodium-sumo | 0.8.4 | ISC | Existing upstream encryption dependency |
| @nextcloud/auth, axios, browser-storage, capabilities, event-bus, initial-state, l10n, logger, router | See inventory | GPL-3.0-or-later | Transitive Nextcloud component dependencies |
| @mdi/js | 7.4.47 | Apache-2.0 (icons; see original Pictogrammers notice) | Already embedded in Nextcloud Vue's distributed `mdi.mjs` chunk |
| @vitejs/plugin-vue | 6.0.11 | MIT | Official Vue build plugin; not shipped as application code |
| vite | 7.3.8 | MIT | Build tool; not shipped as application code |
| esbuild | 0.25.12 | MIT | Existing client test bundler; not shipped as application code |
| axe-core | 4.14.1 | MPL-2.0 | Development accessibility checks; not shipped as application code |

## Exact inventory and fail-closed checks

[`scripts/runtime-licenses.json`](scripts/runtime-licenses.json) is the reviewed, machine-readable inventory of **292 package paths**, including nested versions. It pins each package's name, version, declared license, npm tarball integrity, and SHA256 hashes of the original notice files. Its graph includes production dependencies, optional dependencies and required peers. This deliberately over-includes packages whose code Vite removes, including some type and compiler packages.

Optional-only peer integrations are not followed: for example, Vue Router's optional Vite integration is a build tool, not browser application code. This exclusion is checked against the **actual emitted bundle**. The Vite build records dependency module paths and SHA256 of both emitted assets in `.build/bundle-modules.json`; the release script refuses an unmatched asset, an unreviewed package, a missing module input or an unsafe path. Build metadata also binds the complete frontend source tree and build configuration/lockfile hashes, rejects development output and excludes test fixtures or external runtime imports. `BUILD.json` records the contributing package paths and module count. The build report is local evidence, not a shipped runtime asset.

Every release ZIP contains **`THIRD_PARTY_LICENSES.txt`**. The generator collects complete original notice files from the locked installation, plus the explicitly sourced files described below. It supports GPL/AGPL, Apache, MIT, ISC, BSD, BlueOak and dual-license notices without treating MIT wording as a universal validity test. Supplemental `NOTICE` files are retained where present. Installed metadata, pinned file hashes, missing notices, symlinks and dependency-set changes are checked; drift stops packaging. The ZIP's `BUILD.json` SHA256 inventory covers the complete generated notices file.

### Original notices absent from npm tarballs

Several upstream npm distributions omit their repository license files. The original notices in [`licenses/npm/`](licenses/npm/) are copied without modification from immutable upstream commits, and their URLs and SHA256 values are recorded in the inventory:

- **@nextcloud/vue 9.14.1:** npm registry `gitHead` `19a99446e594757a50a36a9ac4589d9a9c702259`; original `LICENSES` files and `REUSE.toml` preserve the upstream license and attribution information. These include supplementary licenses for upstream source assets/documentation, not a relicensing of this app.
- **@nextcloud/event-bus 3.3.3:** registry `gitHead` `4dfdb6fd5a84a33a071ff1220cb4a35a581602f2`; original GPL text and `REUSE.toml`.
- **@nodable/entities 3.1.0:** registry `gitHead` `ac48e7ea591da372be023a481875c747535812b3`; original MIT license.
- **blurhash 2.0.5:** upstream version-bump commit `cb151cab5b7d9cd3eef624e12e30381c6d292f0d`, whose `TypeScript/package.json` declares 2.0.5; original repository `License.md`.
- **Embedded @mdi/js 7.4.47:** version identified in Nextcloud Vue's distributed `mdi.mjs.map`; original Pictogrammers notice from registry `gitHead` `47d99c7b945bd5c080d9bc9acb4d1c6bc38ef06c`, paired with the original Apache 2.0 text. This code is already embedded upstream and therefore cannot be discovered from this app's npm runtime dependency edges alone.

For `@tokenizer/token`, `agent-base`, `data-uri-to-buffer` and `https-proxy-agent`, the full original MIT notice is embedded in the installed `README.md`; those hash-pinned original files are included. No new license text is inferred for these packages.

### Explicit exceptions

**passwords-client:** The existing pinned package has no separate license file in the inspected installation. Its metadata declares ISC and names Marius Wieschollek. Precisely this version retains the project's existing reconstructed standard ISC notice, explicitly labelled **not an original upstream license file**. A changed version, license or expected author stops packaging.

**byte-length 1.0.2:** Its package metadata declares MIT, but neither the inspected tarball nor its exact registry source commit contains the original license text. The inventory marks it **`unbundled-only`**. It is a transitive dependency of code that is not used by this UI. Packaging fails if any module from that package contributes to the emitted application. Its source may only be distributed after the original notice has been resolved and reviewed; a license is not fabricated.

## Distribution boundaries

The generated application consists of one bundled ES module and one CSS asset, plus the fixed PHP/template/icon/metadata/notice files. It loads no third-party JavaScript or styles from a CDN, and Node.js/npm are not required on the Nextcloud server. Build tools, `node_modules`, sourcemaps, development fixtures and the notice-source staging directories are not shipped in the runtime ZIP.

Nextcloud and Nextcloud Passwords remain external server dependencies. Their names describe compatibility and do not imply endorsement. Review the inventory, original notices and upstream embedded code when updating dependencies; automated graph and hash checks do not establish the authorship of every transitive source file.
