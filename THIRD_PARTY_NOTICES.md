# Third-party components and licensing

This project is licensed under **AGPL-3.0-or-later** for its own source code. Dependencies remain under their respective licenses. The following versions and license identifiers are declared in the **1.0.0 package-lock.json**:

| Component | Locked version | License |
| --- | --- | --- |
| passwords-client | 1.0.0-beta.6117 | ISC |
| libsodium-wrappers-sumo | 0.8.4 | ISC |
| libsodium-sumo | 0.8.4 | ISC |
| eventemitter3 | 3.1.2 | MIT |
| process | 0.11.10 | MIT |
| querystringify | 2.2.0 | MIT |
| requires-port | 1.0.0 | MIT |
| url-parse | 1.5.10 | MIT |
| esbuild (build tool) | 0.25.12 | MIT |

Source packages and license notices are available through their published npm distributions. The package includes this THIRD_PARTY_NOTICES.md alongside LICENSE. The build uses esbuild's linked legal comments option, and the resulting optional **js/app-100.js.LEGAL.txt** file is included in the release archive when present. **Before publishing a binary**, verify that all notices legally required for the actually bundled dependencies are present and accessible.

Nextcloud and Nextcloud Passwords are **external runtime dependencies**, not code relicensed by this project. Their names are used solely to describe compatibility; this project does not claim upstream endorsement.

**Review limitation:** The list reflects npm metadata; it is not a legal audit of every transitive source file. Update it when dependencies change.
