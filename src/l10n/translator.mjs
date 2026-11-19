import english from './en.json' with {type: 'json'};
import german from './de.json' with {type: 'json'};

const catalogs = Object.freeze({en: english, de: german});
const englishPluralRules = new Intl.PluralRules('en');

/** Choose against the bundled catalogs, independently of the Nextcloud shell. */
export function resolveLocale(languages, language) {
    const preferences = Array.isArray(languages) && languages.length ? languages : [language];
    for (const preference of preferences) {
        if (typeof preference !== 'string' || !preference) continue;
        let locale;
        try { locale = new Intl.Locale(preference); }
        catch (_) { continue; }
        if (Object.hasOwn(catalogs, locale.baseName)) return locale.baseName;
        if (Object.hasOwn(catalogs, locale.language)) return locale.language;
    }
    return 'en';
}

function select(entry, rules, count) {
    if (typeof entry === 'string') return entry;
    if (entry && Number.isFinite(count)) {
        return entry[rules.select(count)];
    }
}

/** Returns plain text. Render it through textContent or escaped Vue bindings. */
export function createTranslator(locale, catalog = catalogs[locale] ?? english) {
    const rules = new Intl.PluralRules(locale);
    return (key, values = {}) => {
        const localized = Object.hasOwn(catalog, key) ? select(catalog[key], rules, values.count) : undefined;
        const fallback = Object.hasOwn(english, key) ? select(english[key], englishPluralRules, values.count) : undefined;
        return (localized ?? fallback ?? key).replace(/\{([a-zA-Z][a-zA-Z0-9]*)\}/g, (placeholder, name) =>
            Object.hasOwn(values, name) ? String(values[name]) : placeholder);
    };
}

export const englishText = createTranslator('en');
