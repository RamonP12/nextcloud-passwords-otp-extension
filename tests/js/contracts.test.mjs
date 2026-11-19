import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync, existsSync} from 'node:fs';
const root = new URL('../../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
function sources(path) {
    return readdirSync(new URL(path, root), {withFileTypes: true}).flatMap(entry => entry.isDirectory()
        ? sources(path + '/' + entry.name) : [path + '/' + entry.name]);
}
const ownCode = () => sources('src').map(read).join('\n');

test('Version, generated asset references and exactly pinned direct dependencies agree', () => {
    const pkg = JSON.parse(read('package.json')), lock = JSON.parse(read('package-lock.json'));
    assert.equal(pkg.version, '1.1.2');
    assert.equal(lock.version, pkg.version); assert.equal(lock.packages[''].version, pkg.version);
    assert.deepEqual(pkg.dependencies, lock.packages[''].dependencies);
    assert.deepEqual(pkg.devDependencies, lock.packages[''].devDependencies);
    for (const version of Object.values({...pkg.dependencies, ...pkg.devDependencies})) assert.match(version, /^\d+\.\d+\.\d+/);
    assert.equal(read('appinfo/info.xml').match(/<version>([^<]+)<\/version>/)?.[1], pkg.version);
    assert.equal(read('templates/main.php').match(/data-template-build="([^"]+)"/)?.[1], pkg.version);
    assert.equal(read('scripts/release.py').match(/^VERSION='([^']+)'/m)?.[1], pkg.version);
    assert.match(read('src/main.js'), /PASSWORDS_OTP_JS_112_VERIFIED/);
    assert.match(read('src/styles.css'), /PASSWORDS_OTP_CSS_112_VERIFIED/);
    assert.equal((read('lib/Controller/PageController.php').match(/'app-112'/g) || []).length, 2);
});

test('Runtime is precompiled Vue3 with Nextcloud9 components and explicit production devtools disabled', () => {
    const pkg = JSON.parse(read('package.json'));
    assert.match(pkg.dependencies.vue, /^3\./); assert.match(pkg.dependencies['@nextcloud/vue'], /^9\./);
    assert.equal(pkg.scripts.build, 'vite build');
    assert.match(read('vite.config.js'), /__VUE_PROD_DEVTOOLS__: false/);
    assert.match(read('vite.config.js'), /sourcemap: false/);
    assert.match(read('src/main.js'), /createApp\(App/);
    assert.doesNotMatch(read('src/main.js'), /template:\s*[`'"]/);
    for (const component of ['NcContent', 'NcAppContent', 'NcButton', 'NcDialog', 'NcTextField', 'NcPasswordField', 'NcSelect']) {
        assert.ok(ownCode().includes('@nextcloud/vue/components/' + component), component);
    }
});

test('Single JS/CSS runtime inventory excludes fixtures and old imperative entry', () => {
    assert.match(read('vite.config.js'), /entryFileNames: 'js\/app-112\.mjs'/);
    assert.match(read('vite.config.js'), /return 'css\/app-112\.css'/);
    assert.match(read('vite.config.js'), /inlineDynamicImports: true/);
    assert.match(read('vite.config.js'), /cssCodeSplit: false/);
    assert.equal(existsSync(new URL('src/ap1/index.js', root)), false);
    assert.doesNotMatch(ownCode(), /fixture-client|__cryptoFixture|__otpTest|__otpReferenceDependencies/);
});

test('Own runtime does not log, inject HTML or persist secrets', () => {
    assert.doesNotMatch(ownCode(), /console\.(log|debug|error|warn)|\.innerHTML\s*=|insertAdjacentHTML|v-html|localStorage|sessionStorage|indexedDB|BroadcastChannel|SharedWorker|document\.cookie/);
});

test('Password fields never use remote strength validation', () => {
    for (const path of ['src/components/OtpCreateDialog.vue', 'src/components/VaultUnlock.vue']) {
        const tags = read(path).match(/<NcPasswordField\b[^>]*>/gs) || [];
        assert.ok(tags.length);
        for (const tag of tags) {
            assert.match(tag, /:check-password-strength="false"/);
            assert.match(tag, /data-otp-secret/);
        }
    }
});

test('Creation remains the only own password mutation endpoint', () => {
    assert.doesNotMatch(ownCode(), /password\/update|password\/delete|share\/create|share\/update|folder\/update/);
    assert.match(read('src/ap1/session.mjs'), /setAcceptedStatusCodes\(\[201\]\)/);
    assert.match(read('src/ap1/session.mjs'), /#createBlocked/);
});

test('Retired HOTP implementation, metrics and manual lock stay absent', () => {
    for (const path of ['src/ap4', 'src/release-policy.mjs', 'js/ap0.js', 'css/ap0.css', 'scripts/matrix.py']) {
        assert.equal(existsSync(new URL(path, root)), false, path);
    }
    assert.doesNotMatch(ownCode(), /hotpNext|importHotpKey|calculateHotp|OTP_HOTP_WRITE_TEST_ONLY|hotp-commit|passwords-otp-ap4|passwords-otp-ap1-lock|passwords-otp-ap0__metrics/);
});

test('Requested German copy is retained and subtree language is explicit', () => {
    const app = read('src/App.vue');
    assert.ok(app.includes('<h1>Passwort OTP Code Generator</h1>'));
    assert.ok(app.includes('OTP-Codes aus deinen eigenen gespeicherten OTP-Passwörtern sowie aus den mit dir geteilten OTP-Passwörtern'));
    assert.ok(app.includes('Hier kann ein neuer OTP Eintrag zu deinen Passwörtern hinzugefügt werden.'));
    assert.ok(app.includes('Neues OTP Passwort hinzufügen'));
    assert.match(read('templates/main.php'), /lang="de"/);
    assert.match(read('src/components/OtpCreateDialog.vue'), /lang="de"/);
    assert.doesNotMatch(app, /NextCloud|Desktop-Testversion/);
});

test('HTML bootstrap remains non-secret and module assets remain generated', () => {
    const template = read('templates/main.php');
    assert.doesNotMatch(template, /<script|<input|token|password.*value=/i);
    assert.match(template, /passwords-otp-dialog-host/);
    const ignore = read('.gitignore').split('\n');
    for (const line of ['js/app-*.js', 'js/app-*.mjs', 'css/app-*.css']) assert.ok(ignore.includes(line));
});

test('Sensitive domain classes stay outside deep Vue reactivity', () => {
    assert.doesNotMatch(read('src/ui/controller.mjs'), /from ['"]vue['"]|reactive\(|shallowReactive\(/);
    assert.match(read('src/App.vue'), /shallowRef/);
    assert.doesNotMatch(ownCode(), /ref\(session\)|reactive\(session\)|reactive\(client\)|ref\(presenter\)/);
});

test('Initial state, request protections and exact wrong-master retry contracts retained', () => {
    const php = read('lib/Controller/PageController.php'), session = read('src/ap1/session.mjs');
    assert.match(php, /private, no-store, max-age=0/);
    assert.match(php, /hash_equals\(\$current, \$expected\)/);
    assert.match(php, /allowEvalWasm\(true\)/);
    assert.match(session, /body\?\.id === 'ab6e13ba'/);
    assert.match(session, /safeStatusCode\(error\) !== 401/);
    assert.doesNotMatch(session, /body\?\.id === '033d1943'/);
});
