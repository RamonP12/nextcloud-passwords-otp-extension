# Third-party components and licensing

This project is **AGPL-3.0-or-later** for its own source code. Bundled libraries retain their original licenses. All versions below are pinned by the 1.0.0 package lockfile.

| Component | Locked version | License | Distribution |
| --- | --- | --- | --- |
| passwords-client | 1.0.0-beta.6117 | ISC | Bundled runtime |
| libsodium-wrappers-sumo | 0.8.4 | ISC | Bundled runtime |
| libsodium-sumo | 0.8.4 | ISC | Bundled runtime |
| eventemitter3 | 3.1.2 | MIT | Bundled runtime |
| process | 0.11.10 | MIT | Bundled runtime |
| querystringify | 2.2.0 | MIT | Bundled runtime |
| requires-port | 1.0.0 | MIT | Bundled runtime |
| url-parse | 1.5.10 | MIT | Bundled runtime |
| esbuild | 0.25.12 | MIT | Build tool only, not shipped |

## Complete third-party notices in the release archive

Every generated release ZIP must contain **THIRD_PARTY_LICENSES.txt**, with the complete copyright and permission notices of each bundled runtime dependency. The release script reads the original notices directly from the installed locked npm packages, verifies their declared name, version and license, and rejects missing or unreviewed dependencies. The resulting notices file is covered by the ZIP's BUILD.json SHA256 inventory.

**Special case: passwords-client.** This pinned npm package does not contain a separate LICENSE file in the inspected installation. Its package metadata declares ISC and names Marius Wieschollek as the author. For precisely this pinned version, the generator supplies a reconstructed standard ISC notice with that attribution, clearly identified as **not an original upstream license file**. A changed version or missing expected metadata stops the build.

esbuild's optional **js/app-100.js.LEGAL.txt** contains only build-preserved legal comments. It is supplementary and cannot replace the complete license file. esbuild itself is a build-only dependency and is not distributed in the release ZIP.

Nextcloud and Nextcloud Passwords are external runtime dependencies; their code is not relicensed by this project. Their names are used solely to describe compatibility and do not imply an endorsement.

**Review limitation:** The automated inventory validates the npm dependency graph and supplied notices, not the authorship of every transitive source file. Review the notice inventory when dependencies change.
