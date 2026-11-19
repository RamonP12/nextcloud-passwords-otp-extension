import {defineConfig} from 'vite';
import vue from '@vitejs/plugin-vue';
import {createHash} from 'node:crypto';
import {mkdirSync, readFileSync, readdirSync, writeFileSync} from 'node:fs';
import {relative, resolve} from 'node:path';

/** Bind reviewed dependencies to modules in the output. Build-only metadata. */
function bundleInventory() {
    let sourceInputs;
    let mode, command;
    function inputs() {
        const files = ['package.json', 'package-lock.json', 'vite.config.js'];
        function visit(directory) {
            for (const entry of readdirSync(directory, {withFileTypes: true})) {
                const path = `${directory}/${entry.name}`;
                if (entry.isSymbolicLink()) throw new Error('Symlink in frontend source');
                if (entry.isDirectory()) visit(path);
                else if (entry.isFile()) files.push(path);
                else throw new Error('Nonregular frontend input');
            }
        }
        visit('src');
        return Object.fromEntries(files.sort().map(path => [path,
            createHash('sha256').update(readFileSync(path)).digest('hex')]));
    }
    return {
        name: 'otp-bundle-inventory',
        configResolved(config) { mode = config.mode; command = config.command; },
        buildStart() { sourceInputs = inputs(); },
        generateBundle: {
            order: 'post',
            handler(_options, bundle) {
                const css = bundle['css/app-110.css'];
                if (css?.type !== 'asset' || typeof css.source !== 'string') {
                    throw new Error('Missing final CSS asset for installer marker');
                }
                // CSS minification removes source comments. Preserve the
                // installer's fixed build sentinel in the final output before
                // writeBundle binds the emitted bytes to source/module hashes.
                css.source = '/*! PASSWORDS_OTP_CSS_110_VERIFIED */\n' + css.source;
            },
        },
        writeBundle(_options, bundle) {
            if (JSON.stringify(sourceInputs) !== JSON.stringify(inputs())) throw new Error('Frontend changed during compilation');
            const assets = {};
            const modules = new Set();
            const buildModules = new Set();
            for (const [path, item] of Object.entries(bundle)) {
                if (!['js/app-110.mjs', 'css/app-110.css'].includes(path)) {
                    throw new Error(`Unexpected runtime asset: ${path}`);
                }
                assets[path] = createHash('sha256').update(readFileSync(resolve(path))).digest('hex');
                if (item.type === 'chunk' && (item.imports.length || item.dynamicImports.length)) {
                    throw new Error('Runtime imports are outside the fixed asset inventory');
                }
                for (const id of Object.keys(item.modules || {})) {
                    if (['\0commonjsHelpers.js', '\0commonjs-dynamic-modules', '\0vite/preload-helper.js'].includes(id)) continue;
                    const normalized = id.replaceAll('\0', '').split('?')[0];
                    const path = relative(process.cwd(), normalized);
                    if (!path.startsWith('src/') && !path.startsWith('node_modules/')) {
                        throw new Error(`Foreign module in production bundle: ${path}`);
                    }
                    buildModules.add(path);
                    if (path.startsWith('node_modules/')) modules.add(path);
                }
            }
            if (Object.keys(assets).length !== 2) throw new Error('Missing compiled JS/CSS asset');
            mkdirSync('.build', {recursive: true});
            writeFileSync('.build/bundle-modules.json', JSON.stringify({schema: 2, mode, command, assets,
                source_inputs: sourceInputs, build_modules: [...buildModules].sort(),
                modules: [...modules].sort()}, null, 2) + '\n');
        },
    };
}

// The explicit, small configuration avoids unused Node crypto polyfills and
// development generators in the shared app preset. Vue components stay native.
// Nextcloud resolves .mjs assets itself; this bundle needs no runtime chunks.
export default defineConfig({
        plugins: [vue(), bundleInventory()],
        define: {__VUE_OPTIONS_API__: true, __VUE_PROD_DEVTOOLS__: false, __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false},
        build: {
            outDir: '.',
            emptyOutDir: false,
            target: 'es2022',
            sourcemap: false,
            cssCodeSplit: false,
            modulePreload: false,
            rollupOptions: {
                input: 'src/main.js',
                output: {
                    intro: `const appName = "passwords_otp"; const appVersion = ${JSON.stringify(JSON.parse(readFileSync('package.json', 'utf8')).version)};`,
                    entryFileNames: 'js/app-110.mjs',
                    inlineDynamicImports: true,
                    assetFileNames: info => {
                        if (!info.names.every(name => name.endsWith('.css'))) throw new Error('Unexpected non-CSS runtime asset');
                        return 'css/app-110.css';
                    },
                },
            },
        },
});
