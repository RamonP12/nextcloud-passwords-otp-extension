# Version 1.1.2 verification

Version 1.1.2 adds the enforced Passwords prerequisite and deterministic tar.gz
distribution to the published 1.1.1 Nextcloud Vue edition. The UI wording,
TOTP calculation, encrypted vault handling and create-only product scope remain
unchanged. This record covers the new source and does not reuse old test totals
as proof of the changed backend behavior.

The final version-bound results and reviewed source hashes are recorded in
`docs/validation/1.1.2/`. The GitHub Release's `BUILD.json` binds its archives to
the exact published source commit; final archive checksums are attached to that
release. Build provenance changes when a documentation/evidence commit changes
the source commit, even if compiled runtime bytes are unchanged.

## Evidence scope

All verification is local. GitHub Actions is unavailable and has not been
dispatched. The retained workflow has only an explicit manual trigger.

- JavaScript tests cover the existing parser/crypto, transport, session,
  creation and presentation contracts.
- Pinned Passwords client/libsodium tests use the actual dependencies with
  synthetic upstream responses.
- Python tests cover packages, licenses, source provenance, deployment gates,
  rollback and adversarial TAR/signature cases. Cryptographic tests use
  ephemeral synthetic certificates, never a trusted production app certificate.
- PHP contracts exercise dependency state, per-user access, event handling,
  job cleanup, migration behavior and the original controller/session safeguards.
- The Nextcloud core-component suite loads unchanged upstream core classes
  pinned by SHA256, using isolated framework/database services. It exercises
  actual installer, migration, app-manager, repair, event and CLI code. It is
  **not** a running Nextcloud/Passwords instance.
- The compiled browser suite loads the production Vue assets in a synthetic
  HTTPS shell/API. It is not live-server routing or authenticated Passwords
  acceptance.
- Metadata is checked against Nextcloud 35's official XSD. Repeated compiled
  builds and both archive formats must be byte-identical for the same commit.

## Installed-server and publication boundaries

The maintainer accepted five functional checks on candidate 1.1.0 in the existing
Nextcloud 35.0.2.2 / Passwords 2026.11.20 / PHP 8.5 / MariaDB localhost fixture.
Those checks are recorded in [1.1.1 verification](VALIDATION_VUE_1.1.1.md).
No 1.1.2 installation or dependency lifecycle acceptance on that laptop is
claimed here. The focused remaining checks are in
[Dependency lifecycle](DEPENDENCY_LIFECYCLE.md).

The release is a **manual, unsigned GitHub distribution**. Its tar.gz has the
required single `passwords_otp/` root and compiled runtime payload. Nextcloud
code signing, certificate trust, the detached archive signature, App Store
registration/publication and review of the upstream private API coupling remain
separate requirements. No signing credential was supplied for this release.
`production_approved=false` remains unchanged. No production AIO/PostgreSQL
upgrade approval is inferred from these tests.
