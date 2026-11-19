<script setup>
import {nextTick, onBeforeUnmount, onMounted, ref, shallowRef} from 'vue';
import NcContent from '@nextcloud/vue/components/NcContent';
import NcAppContent from '@nextcloud/vue/components/NcAppContent';
import NcButton from '@nextcloud/vue/components/NcButton';
import NcNoteCard from '@nextcloud/vue/components/NcNoteCard';
import VaultUnlock from './components/VaultUnlock.vue';
import OtpCreateDialog from './components/OtpCreateDialog.vue';
import OtpAccountList from './components/OtpAccountList.vue';
import {createOtpController} from './ui/controller.mjs';
import {clearSensitiveDom} from './ui/dom-safety.mjs';
import {createClient, sodiumReady} from './ap1/upstream.js';

const props = defineProps({config: {type: Object, required: true},
    onControllerReady: {type: Function, required: true}});
const state = shallowRef({mode: 'loading', status: 'Sitzung wird geprüft …', statusType: 'info'});
const unlockForm = ref(null), createDialog = ref(null);
const scrubRevision = ref(0);
function clear(options) {
    if (options.codes) scrubRevision.value++;
    if (options.inputs) {
        unlockForm.value?.clearSecrets();
        createDialog.value?.clearSecrets();
    }
    clearSensitiveDom(document, options);
}
function focus(name) {
    void nextTick(() => {
        if (name === 'master' || name === 'token') unlockForm.value?.focus(name);
        else if (name === 'create') document.getElementById('passwords-otp-ap12-open')?.focus();
        else createDialog.value?.focus(name);
    });
}
// Intentionally plain closure; never proxy the session or use a global store.
const controller = createOtpController({config: props.config, pageUrl: window.location.href,
    doc: document, fetcher: (...args) => fetch(...args), createClient, sodiumReady,
    publish: value => { state.value = value; }, clear, focus});
// Register synchronously in setup. Waiting for mount() to return would leave a
// failure in the initial render or mounted hooks unable to stop authentication.
props.onControllerReady(controller.fail);
const visibility = () => controller.visibilityChanged();
const focused = () => controller.focusChanged();
const leaving = () => controller.pageHide();
const returning = event => controller.pageShow(event);
onMounted(() => {
    document.addEventListener('visibilitychange', visibility);
    window.addEventListener('focus', focused);
    window.addEventListener('pagehide', leaving);
    window.addEventListener('pageshow', returning);
    void controller.start();
});
onBeforeUnmount(() => {
    controller.pageHide();
    document.removeEventListener('visibilitychange', visibility);
    window.removeEventListener('focus', focused);
    window.removeEventListener('pagehide', leaving);
    window.removeEventListener('pageshow', returning);
});
defineExpose({fail: controller.fail});
const reload = () => window.location.reload();
</script>

<template>
    <NcContent app-name="passwords_otp" lang="de">
        <NcAppContent>
            <div class="passwords-otp-panel">
                <header class="passwords-otp-header">
                    <h1>Passwords OTP Generator</h1>
                    <p class="passwords-otp-secondary">OTP-Codes aus deinen eigenen gespeicherten OTP-Passwörtern sowie aus den mit dir geteilten OTP-Passwörtern</p>
                </header>
                <div id="passwords-otp-ap1-status" :role="state.statusType === 'error' ? 'alert' : 'status'"
                    :aria-live="state.statusType === 'error' ? 'assertive' : 'polite'">
                    <NcNoteCard :type="state.statusType">{{ state.status }}</NcNoteCard>
                </div>
                <VaultUnlock v-if="state.mode === 'needs-auth'" ref="unlockForm"
                    :snapshot="state.snapshot" :busy="state.unlockBusy" :error="state.unlockError"
                    @unlock="controller.unlock" />
                <div v-if="state.mode === 'ready'" class="passwords-otp-toolbar" data-otp-protected>
                    <NcButton id="passwords-otp-ap12-open" variant="primary" :disabled="state.createOpening || state.createBusy"
                        aria-haspopup="dialog" :aria-controls="state.createOpen ? 'passwords-otp-ap12-dialog' : undefined" aria-describedby="passwords-otp-ap12-help"
                        @click="controller.openCreate">
                        {{ state.createOpening ? 'Sitzung wird geprüft …' : 'Neues OTP Passwort hinzufügen' }}
                    </NcButton>
                    <p id="passwords-otp-ap12-help" class="passwords-otp-secondary">Hier kann ein neuer OTP Eintrag zu deinen Passwörtern hinzugefügt werden. Er wird in der Passwords App zusammen mit deinen anderen Passwörtern gespeichert und kann über die Passwords App auch verwaltet (gelöscht, verändert) und mit anderen Nextcloud Benutzern geteilt werden.</p>
                </div>
                <OtpAccountList v-if="state.mode === 'ready'" :view="state.otp" :query="state.query" :feedback="state.feedback" :scrub-revision="scrubRevision"
                    @filter="controller.filter" @copy="controller.copy" />
                <NcButton v-if="state.canReload" id="passwords-otp-ap1-reload" variant="primary"
                    @click="reload">Seite neu laden</NcButton>
            </div>
        </NcAppContent>
        <OtpCreateDialog v-if="state.createOpen" ref="createDialog" :busy="state.createBusy" :error="state.createError"
            @close="controller.closeCreate" @create="controller.create" />
    </NcContent>
</template>
