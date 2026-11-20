# Interface localization

The app selects German (`de`) or English (`en`) for its own interface. English is the source catalog and fallback. This feature is available in 1.1.4. The published 1.1.3 packages contain the German interface.

## Browser and Nextcloud language settings

1. Read the ordered `navigator.languages` list. Use `navigator.language` when the list is missing or empty.
2. Canonicalize each BCP 47 language tag. Try the locale and then its base language against the bundled catalogs. Skip unusable tags and continue until a preference matches.
3. Use English if no preference matches. An untranslated catalog key or plural form also falls back to English.

| Browser preferences | App body |
| --- | --- |
| `de-DE` or `de-CH` | German |
| `en-US` | English |
| `fr-FR` only | English |
| `fr-FR`, then `de-CH` | German |
| No usable preference | English |

The locale is resolved once when the app loads. Reload or reopen the app after changing browser preferences. An in-tab language change leaves the current vault session active. The app root and dialog portal declare their language for assistive technology. The server-rendered loading and JavaScript-required messages use English before the client resolves its locale.

Nextcloud determines the shell language through its own account and server policy, including `force_language`. The app uses its own bundled catalogs because Nextcloud Vue's default translator follows the shell. The menu and Apps page use Nextcloud metadata and keep the product name **Passwords OTP Generator**. The summary and description in `appinfo/info.xml` have English and German variants for the shell. Authenticator provider names and stored labels, usernames and issuers are displayed as supplied. The create dialog uses its localized **Cancel** or **Abbrechen** button and Escape. The fallback title for an unnamed account, the tab-switch warning in the create dialog and the copy control's session-check message also follow the selected locale.

## Maintaining the catalogs

- Edit the English source in [`src/l10n/en.json`](../src/l10n/en.json) and the German translation in [`src/l10n/de.json`](../src/l10n/de.json). Match keys and named placeholders in both. For counted text, supply the plural forms used by the locale.
- To add a language, register its catalog in [`src/l10n/translator.mjs`](../src/l10n/translator.mjs) and extend locale, plural and browser coverage. Use Vue text bindings or DOM `textContent` for translated text. Keep machine fault codes and API data out of the catalogs.
- Keep OTP codes and secrets unchanged. Plural selection and interpolation apply to display text. The build bundles the catalogs in the production ES module.

For the platform language policy and localization APIs, see [Nextcloud language configuration](https://docs.nextcloud.com/server/stable/admin_manual/configuration_server/language_configuration.html) and [Nextcloud translations](https://docs.nextcloud.com/server/stable/developer_manual/basics/front-end/l10n.html).

## Verification

Run `npm test`, `npm run build` and `npm run test:browser`. The unit tests cover preference order, regional variants, invalid and empty preferences, key and placeholder parity, fallback and plurals. The browser suite covers both locales with the production bundle, including copy feedback, native required-field validation, the dialog's accessible name and a master-passphrase/secondary-factor challenge against synthetic server responses.

For the real Nextcloud language matrix and session checks, see [integration acceptance](../tests/integration/README.md#browser-language-matrix).

### Verification of PR #21

- Nextcloud **35.0.3.2**, Passwords **2026.11.20**, PHP **8.4.27**, SQLite and Chromium **156.0.8078.79** on a disposable loopback HTTPS fixture. All six language cases passed, including conflicting account preferences and both values of `force_language`. Axe checked the app and creation dialog in each case.
- All six live core checks passed. They verified the real HTTP assets and security headers, a shared read-only record, new-entry creation, TOTP against independent HMAC, the native clipboard, keyboard focus, removal of protected content after session expiry, group authorization and the CSE master-passphrase retry and encrypted creation.
- All 40 compiled-browser cases passed. Passwords' `two-factor-tokens` feature was disabled in the live fixture. The 2FA presentation and retry used synthetic challenge responses with the production bundle and pinned client.
- The 243 JavaScript tests, 17 pinned-client tests, 102 Python tests, 177 PHP assertions and the Nextcloud metadata schema check passed. npm audit reported zero vulnerabilities. The development ZIP and TAR.GZ passed deterministic packaging and integrity checks.

These results cover the original [localization change in PR #21](https://github.com/RamonP12/nextcloud-passwords-otp-extension/pull/21). The [development CI record](DEVELOPMENT.md#verification-on-2026-11-20) covers the later compiled-browser suite, including the fallback title and tab-switch warning in both languages.
