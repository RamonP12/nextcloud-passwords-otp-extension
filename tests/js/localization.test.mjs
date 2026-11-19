import test from 'node:test';
import assert from 'node:assert/strict';
import english from '../../src/l10n/en.json' with {type: 'json'};
import german from '../../src/l10n/de.json' with {type: 'json'};
import {createTranslator, resolveLocale} from '../../src/l10n/translator.mjs';
import {otpListNotice} from '../../src/ap2/view.mjs';

test('Browser preferences are ordered, canonicalized and matched by locale or base language', () => {
    assert.equal(resolveLocale(['DE-ch-u-nu-arab', 'en-US']), 'de');
    assert.equal(resolveLocale(['en-GB', 'de-DE']), 'en');
    assert.equal(resolveLocale(['fr-CH', 'de-AT', 'en']), 'de');
    assert.equal(resolveLocale(['de', 'en']), 'de');
    assert.equal(resolveLocale(['es', 'en']), 'en');
});

test('Missing or empty preference lists use navigator.language, and unusable preferences fall back to English', () => {
    assert.equal(resolveLocale(undefined, 'de-CH'), 'de');
    assert.equal(resolveLocale([], 'de-CH'), 'de');
    assert.equal(resolveLocale(['fr', '', 'de_CH', {}, null, 'constructor'], 'de'), 'en');
    assert.equal(resolveLocale(['fr', 'de_CH', 'de-DE']), 'de');
    assert.equal(resolveLocale(undefined, 'de_CH'), 'en');
    assert.equal(resolveLocale(), 'en');
});

test('Both catalogs cover the same keys, plural forms and interpolation arguments', () => {
    assert.deepEqual(Object.keys(german).sort(), Object.keys(english).sort());
    const placeholders = template => Array.from(template.matchAll(/\{(\w+)\}/g), match => match[1]).sort();
    for (const [key, entry] of Object.entries(english)) {
        if (typeof entry === 'string') {
            assert.deepEqual(placeholders(german[key]), placeholders(entry), key);
        } else {
            assert.deepEqual(Object.keys(german[key]).sort(), ['one', 'other'], key);
            for (const form of ['one', 'other']) {
                assert.deepEqual(placeholders(german[key][form]), placeholders(entry[form]), key);
            }
        }
    }
});

test('Plural messages and list warnings are grammatical without affecting account values', () => {
    const de = createTranslator('de'), en = createTranslator('en');
    assert.deepEqual([0, 1, 2].map(count => de('seconds', {count})), ['0 Sekunden', '1 Sekunde', '2 Sekunden']);
    assert.deepEqual([0, 1, 2].map(count => en('seconds', {count})), ['0 seconds', '1 second', '2 seconds']);
    const snapshot = {state: 'ready', invalidOtpCount: 1, unsupportedOtpCount: 2};
    assert.match(otpListNotice(snapshot, 0, en), /1 OTP entry was hidden.*2 OTP entries/);
    assert.match(otpListNotice(snapshot, 0, de), /1 OTP-Eintrag .*2 OTP-Einträge/);
});

test('Missing translations use English and arguments are interpolated as literal text', () => {
    const t = createTranslator('de', {'copy-account': 'Kopieren für {title}'});
    assert.equal(t('reload'), 'Reload page');
    assert.equal(t('seconds', {count: 1}), '1 second');
    const partial = createTranslator('de', {seconds: {other: '{count} Sekunden'}});
    assert.equal(partial('seconds', {count: 1}), '1 second');
    assert.equal(partial('seconds', {count: 2}), '2 Sekunden');
    assert.equal(t('copy-account', {title: '<img src="fixture"> $& {title}'}), 'Kopieren für <img src="fixture"> $& {title}');
    assert.equal(t('copy-account', Object.create({title: 'inherited'})), 'Kopieren für {title}');
});
