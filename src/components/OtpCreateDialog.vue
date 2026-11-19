<script setup>
import {computed, nextTick, onBeforeUnmount, onMounted, ref, watch} from 'vue';
import NcButton from '@nextcloud/vue/components/NcButton';
import NcDialog from '@nextcloud/vue/components/NcDialog';
import NcTextField from '@nextcloud/vue/components/NcTextField';
import NcPasswordField from '@nextcloud/vue/components/NcPasswordField';
import NcNoteCard from '@nextcloud/vue/components/NcNoteCard';
import {createErrorMessage} from '../ui/messages.mjs';

const props = defineProps({busy: Boolean, error: String});
const emit = defineEmits(['close', 'create']);
const label = ref(''), username = ref(''), password = ref(''), secret = ref('');
const labelField = ref(null), secretField = ref(null), feedback = ref(null);
const errorMessage = computed(() => props.error ? createErrorMessage(props.error) : '');
const invalid = field => props.error === `create-invalid-${field}`;
function clearSecrets() { password.value = ''; secret.value = ''; }
function close() {
    if (props.busy) return;
    clearSecrets();
    emit('close');
}
function submit(event) {
    if (props.busy || !event.target.reportValidity()) return;
    const values = {label: label.value, username: username.value, password: password.value, secret: secret.value};
    clearSecrets();
    emit('create', values);
}
function onDialogKeydown(event) {
    if (props.busy && event.key === 'Tab') {
        // Disabling the submit control can otherwise move focus to the page
        // body. There is no active action to tab to while the POST is pending.
        event.preventDefault();
        feedback.value?.focus();
        return;
    }
    // NcModal activates its focus trap only after the opening transition.
    // Keep keyboard containment and Escape available during that interval too.
    if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        close();
        return;
    }
    if (event.key === 'Tab' && !event.defaultPrevented) {
        const dialog = event.currentTarget;
        const controls = [...dialog.querySelectorAll('input, select, textarea, button, a[href], [tabindex]')]
            .filter(element => !element.disabled && element.tabIndex >= 0
                && element.getClientRects().length > 0 && !element.closest('[hidden]'));
        const first = controls[0], last = controls.at(-1), current = document.activeElement;
        if (!first) {
            event.preventDefault();
            dialog.focus();
        } else if (!controls.includes(current) || (event.shiftKey && current === first)
                || (!event.shiftKey && current === last)) {
            event.preventDefault();
            (event.shiftKey ? last : first).focus();
        }
        return;
    }
    // Creating a password remains an explicit save action. Enter/Space on the
    // Save button works normally, including assistive-technology activation.
    if (event.key === 'Enter' && event.target.tagName === 'INPUT') event.preventDefault();
}
function focus(name) {
    void nextTick(() => {
        if (name === 'label') labelField.value?.focus();
        else if (name === 'secret') secretField.value?.focus();
        else feedback.value?.focus();
    });
}
watch(() => props.error, value => { if (value) focus(invalid('secret') ? 'secret' : 'error'); });
watch(() => props.busy, value => { if (value) focus('status'); }, {flush: 'post', immediate: true});
onMounted(() => focus('label'));
onBeforeUnmount(() => { clearSecrets(); label.value = ''; username.value = ''; });
defineExpose({clearSecrets, focus});
</script>

<template>
    <NcDialog id="passwords-otp-ap12-dialog" class="passwords-otp-dialog" lang="de"
        name="Neues OTP Passwort hinzufügen" size="normal" is-form
        container="#passwords-otp-dialog-host" :open="true" :no-close="busy"
        :close-on-click-outside="false" :out-transition="false"
        content-classes="passwords-otp-form" :aria-busy="busy" data-otp-protected
        @submit="submit" @closing="close" @update:open="value => { if (!value) close(); }"
        @keydown.capture="onDialogKeydown">
        <p id="passwords-otp-ap12-description">Einen neuen Eintrag in Nextcloud Passwords erstellen. Das OTP-Datenfeld wird automatisch angelegt.</p>
        <NcTextField id="passwords-otp-ap12-label" ref="labelField" v-model="label"
            label="Bezeichnung" required :maxlength="160" autocomplete="off"
            :disabled="busy" :error="invalid('label')" :aria-invalid="invalid('label')" />
        <NcTextField id="passwords-otp-ap12-username" v-model="username"
            label="Benutzername (optional)" :maxlength="160" autocomplete="off"
            :disabled="busy" :error="invalid('username')" :aria-invalid="invalid('username')" spellcheck="false" />
        <NcPasswordField id="passwords-otp-ap12-password" v-model="password"
            label="Passwort" required :maxlength="4096" autocomplete="new-password"
            :check-password-strength="false" :show-trailing-button="false" :disabled="busy"
            :error="invalid('password')" :aria-invalid="invalid('password')" data-otp-secret
            helper-text="Passwort des Dienstkontos, nicht das Nextcloud-Masterpasswort."
            spellcheck="false" autocapitalize="off" />
        <NcPasswordField id="passwords-otp-ap12-secret" ref="secretField" v-model="secret"
            label="OTP-Secret (Base32)" required :maxlength="4096" autocomplete="off"
            :check-password-strength="false" :show-trailing-button="false" :disabled="busy"
            :error="invalid('secret')" :aria-invalid="invalid('secret')" data-otp-secret
            helper-text="Einrichtungsschlüssel des Dienstes. Neuanlage: SHA-1, 6 Stellen, 30 Sekunden."
            spellcheck="false" autocapitalize="off" />
        <p class="passwords-otp-secondary">Mit «OTP speichern» bestätigen. Enter in einem Eingabefeld erstellt keinen Eintrag.</p>
        <div id="passwords-otp-ap12-feedback" ref="feedback" tabindex="-1"
            :role="error ? 'alert' : 'status'" :aria-live="error ? 'assertive' : 'polite'">
            <NcNoteCard v-if="error" type="error">{{ errorMessage }}</NcNoteCard>
            <span v-else-if="busy">Neuer OTP-Eintrag wird erstellt …</span>
        </div>
        <template #actions>
            <NcButton id="passwords-otp-ap12-cancel" :disabled="busy" @click="close">Abbrechen</NcButton>
            <NcButton id="passwords-otp-ap12-save" type="submit" variant="primary" :disabled="busy">
                {{ busy ? 'Wird gespeichert …' : 'OTP speichern' }}
            </NcButton>
        </template>
    </NcDialog>
</template>

<style>
/* NcModal activates its focus trap only after the entrance transition. This
 * sensitive form must have focus protection immediately, including rapid
 * submit/pagehide sequences. Keep the override restricted to this dialog. */
.passwords-otp-dialog.modal-mask,
.passwords-otp-dialog .modal-wrapper,
.passwords-otp-dialog .modal-container {
    transition: none !important;
}
</style>
