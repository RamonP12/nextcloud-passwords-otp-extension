# Passwords dependency lifecycle verification

The dependency unit suite uses framework doubles. The component suite loads
unmodified, hash-pinned Nextcloud **35.0.2** core classes with controlled
persistence, metadata and Passwords types. Live browser acceptance is a separate
check. [Live integration](README.md)

## Reproduce the core-component suite

From the repository root with PHP 8.3–8.5 including SimpleXML and Python 3.10+:

```sh
python3 tests/integration/nextcloud_lifecycle.py --fetch-sources
python3 tests/integration/nextcloud_lifecycle.py
```

The first invocation downloads the tagged source files listed in
`nextcloud-35.0.2-sources.json` and checks every size and SHA-256 digest.
Subsequent runs use the same verified files. Select a PHP binary with `--php`
and a source cache with `--source-dir`. The report in
`.build/lifecycle-core/report.json` binds the tested application and core
files to the results.

| Test | Expected behavior |
| --- | --- |
| Fresh registration with missing, disabled, incompatible or updating Passwords | The schema migration denies registration and writes no OTP tables. |
| Existing OTP instance and Passwords disable, removal or version drift | The runtime guard denies access and preserves the OTP scope. |
| Passwords restored in the allowed maintenance line | The runtime guard accepts access again. |
| Manual OTP disable | Passwords recovery preserves the administrator's explicit disablement. |
| Passwords group restriction | The same installation can give different users different permissions. |
| Upgrade or retained migration history | The runtime guard controls access independently of migration history. |
| Previously registered background job | Starting it removes its old registration. |

The suite includes the original negative control that Nextcloud's ordinary
repair runner catches thrown exceptions. First registration uses a schema-only
migration instead. The original v1.1.3 results document the historical
self-disable policy. [Published 1.1.3 verification](../../docs/VALIDATION_1.1.3.md)
