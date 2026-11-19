<script setup>
import {computed, nextTick, onBeforeUnmount, ref} from 'vue';
import NcButton from '@nextcloud/vue/components/NcButton';
import NcTextField from '@nextcloud/vue/components/NcTextField';
import NcPasswordField from '@nextcloud/vue/components/NcPasswordField';
import NcSelect from '@nextcloud/vue/components/NcSelect';

import {clearFieldValidation, localizeInvalidField} from '../ui/form-validation.mjs';

const props = defineProps({snapshot: {type: Object, required: true}, t: {type: Function, required: true}, busy: Boolean, error: String});
const emit = defineEmits(['unlock']);
const password = ref(''), code = ref(''), selectedProvider = ref(null);
const masterField = ref(null), tokenField = ref(null);
const providers = computed(() => props.snapshot.providers.filter(provider => provider.supported));
const provider = computed({
    get: () => selectedProvider.value || providers.value[0] || null,
    set: value => { selectedProvider.value = value; },
});
function clearSecrets() { password.value = ''; code.value = ''; }
function focus(name) { void nextTick(() => (name === 'master' ? masterField : tokenField).value?.focus()); }
function submit(event) {
    if (props.busy || !event.target.reportValidity()) return;
    const auth = {password: password.value, otpCode: code.value, providerId: provider.value?.id || ''};
    clearSecrets();
    emit('unlock', auth);
}
onBeforeUnmount(clearSecrets);
defineExpose({clearSecrets, focus});
</script>

<template>
    <form id="passwords-otp-ap1-login" class="passwords-otp-form" autocomplete="off"
        data-otp-protected :aria-busy="busy" @submit.prevent="submit"
        @invalid.capture="localizeInvalidField($event, t)">
        <NcPasswordField v-if="snapshot.needsChallenge" id="passwords-otp-ap1-password"
            ref="masterField" v-model="password" :label="t('master-key')"
            :check-password-strength="false" :show-trailing-button="false"
            :minlength="12" :maxlength="128" required autocomplete="off" @input="clearFieldValidation"
            :error="Boolean(error)" :aria-invalid="Boolean(error)" :disabled="busy"
            :aria-describedby="error ? 'passwords-otp-ap1-status' : undefined"
            data-otp-secret spellcheck="false" autocapitalize="off" />
        <template v-if="snapshot.needsToken">
            <NcSelect v-model="provider" input-id="passwords-otp-ap1-provider"
                :input-label="t('second-factor')" :aria-label-combobox="t('second-factor')"
                :aria-label-listbox="t('second-factor')" label="label"
                :options="providers" :clearable="false" :searchable="false"
                :append-to-body="false" :disabled="busy" />
            <NcTextField id="passwords-otp-ap1-code" ref="tokenField" v-model="code"
                :label="t('verification-code')" inputmode="numeric" :maxlength="128"
                autocomplete="one-time-code" required @input="clearFieldValidation" :disabled="busy" data-otp-secret
                spellcheck="false" autocapitalize="off" />
        </template>
        <NcButton type="submit" variant="primary" :disabled="busy"
            :aria-label="t(busy ? 'unlock-busy' : 'unlock')">
            {{ t(busy ? 'unlock-busy-status' : 'unlock') }}
        </NcButton>
    </form>
</template>
