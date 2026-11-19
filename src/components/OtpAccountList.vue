<script setup>
import {computed} from 'vue';
import NcButton from '@nextcloud/vue/components/NcButton';
import NcTextField from '@nextcloud/vue/components/NcTextField';
import NcEmptyContent from '@nextcloud/vue/components/NcEmptyContent';
const props = defineProps({view: {type: Object, required: true}, t: {type: Function, required: true}, query: String, feedback: String, scrubRevision: Number});
const emit = defineEmits(['filter', 'copy']);
// A synchronous security scrub can precede Vue's next tick. Reapply the final
// values even if they equal the previous VNode, without remounting the focused
// copy button. These directives only mirror the validated display snapshot.
const repairCode = (el, binding) => { el.textContent = binding.value.code || '—'; };
const repairDisabled = (el, binding) => { el.disabled = binding.value.disabled; };
const repairProgress = (el, binding) => { el.value = binding.value.value; };
const vCode = {mounted: repairCode, updated: repairCode};
const vDisabled = {mounted: repairDisabled, updated: repairDisabled};
const vProgress = {mounted: repairProgress, updated: repairProgress};
const visibleCount = computed(() => props.view.rows.filter(row => !row.hidden).length);
const copyDisabled = row => row.copyDisabled || row.hidden;
function copyCode(event, row) {
    if (event.isTrusted && !copyDisabled(row)) emit('copy', row.account.id);
}
function details(account) {
    const subtitle = [account.issuer, account.accountName, account.username]
        .filter((value, index, values) => value && values.indexOf(value) === index).join(' · ');
    const config = props.t('configuration', {algorithm: account.algorithm.toUpperCase(), digits: account.digits});
    return subtitle ? `${subtitle} · ${config}` : config;
}
</script>

<template>
    <section id="passwords-otp-ap2-section" :aria-label="t('accounts')" data-otp-protected>
        <NcTextField id="passwords-otp-ap2-search" type="search" :model-value="query"
            class="passwords-otp-search" :label="t('search')"
            :placeholder="t('search-placeholder')" autocomplete="off" spellcheck="false"
            @update:model-value="emit('filter', String($event))" />
        <div id="passwords-otp-ap2-empty" role="status" aria-live="polite">
            <NcEmptyContent v-if="visibleCount === 0" :name="t(query ? 'empty-search' : 'empty-accounts')"
                :description="view.notice" />
            <p v-else-if="view.notice" class="passwords-otp-secondary">{{ view.notice }}</p>
        </div>
        <ul id="passwords-otp-ap2-list" class="passwords-otp-list">
            <li v-for="row in view.rows" :key="row.account.id" :hidden="row.hidden" class="passwords-otp-account">
                <div class="passwords-otp-account__metadata">
                    <strong>{{ row.account.title }}</strong>
                    <span class="passwords-otp-secondary">{{ details(row.account) }}</span>
                </div>
                <div class="passwords-otp-account__code">
                    <button type="button" class="passwords-otp-ap3__code"
                        v-code="{code: row.code, revision: scrubRevision}"
                        v-disabled="{disabled: copyDisabled(row), revision: scrubRevision}"
                        :disabled="copyDisabled(row)" :aria-label="t('copy-displayed', {title: row.account.title})"
                        @click="copyCode($event, row)" />
                    <div class="passwords-otp-account__time" aria-live="off">
                        <span>{{ row.code ? t('validity', {count: Math.ceil(row.remainingMs / 1000)}) : t('code-checking') }}</span>
                        <progress v-progress="{value: row.remainingMs / 1000, revision: scrubRevision}" class="passwords-otp-ap3__progress" :max="row.account.period"
                            :value="row.remainingMs / 1000" :aria-label="t('time-remaining', {title: row.account.title})"
                            :aria-valuetext="row.code ? t('seconds', {count: Math.ceil(row.remainingMs / 1000)}) : t('time-checking')" />
                    </div>
                    <NcButton v-disabled="{disabled: copyDisabled(row), revision: scrubRevision}" class="passwords-otp-ap3__copy" :disabled="copyDisabled(row)"
                        :aria-label="t('copy-account', {title: row.account.title})" @click="copyCode($event, row)">
                        {{ t('copy') }}
                    </NcButton>
                </div>
            </li>
        </ul>
        <p id="passwords-otp-ap3-feedback" class="passwords-otp-feedback" role="status" aria-live="polite">{{ feedback }}</p>
    </section>
</template>
