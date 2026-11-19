<script setup>
import {computed} from 'vue';
import NcButton from '@nextcloud/vue/components/NcButton';
import NcTextField from '@nextcloud/vue/components/NcTextField';
import NcEmptyContent from '@nextcloud/vue/components/NcEmptyContent';
const props = defineProps({view: {type: Object, required: true}, query: String, feedback: String, scrubRevision: Number});
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
function details(account) {
    const subtitle = [account.issuer, account.accountName, account.username]
        .filter((value, index, values) => value && values.indexOf(value) === index).join(' · ');
    const config = `TOTP · ${account.algorithm.toUpperCase()} · ${account.digits} Stellen`;
    return subtitle ? `${subtitle} · ${config}` : config;
}
</script>

<template>
    <section id="passwords-otp-ap2-section" aria-label="TOTP-Konten" data-otp-protected>
        <NcTextField id="passwords-otp-ap2-search" type="search" :model-value="query"
            class="passwords-otp-search" label="TOTP-Konten durchsuchen"
            placeholder="Titel, Benutzername oder Anbieter" autocomplete="off" spellcheck="false"
            @update:model-value="emit('filter', String($event))" />
        <div id="passwords-otp-ap2-empty" role="status" aria-live="polite">
            <NcEmptyContent v-if="visibleCount === 0" :name="query ? 'Keine passenden TOTP-Konten' : 'Keine TOTP-Konten'"
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
                    <output v-code="{code: row.code, revision: scrubRevision}" class="passwords-otp-ap3__code" aria-live="off"
                        :aria-label="'Einmalcode für ' + row.account.title" />
                    <div class="passwords-otp-account__time" aria-live="off">
                        <span>{{ row.code ? `Noch ${Math.ceil(row.remainingMs / 1000)} s gültig` : 'Wird geprüft …' }}</span>
                        <progress v-progress="{value: row.remainingMs / 1000, revision: scrubRevision}" class="passwords-otp-ap3__progress" :max="row.account.period"
                            :value="row.remainingMs / 1000" :aria-label="'Restgültigkeit für ' + row.account.title"
                            :aria-valuetext="row.code ? `${Math.ceil(row.remainingMs / 1000)} Sekunden` : 'Wird geprüft'" />
                    </div>
                    <NcButton v-disabled="{disabled: row.copyDisabled || row.hidden, revision: scrubRevision}" class="passwords-otp-ap3__copy" :disabled="row.copyDisabled || row.hidden"
                        :aria-label="'Code kopieren für ' + row.account.title" @click="emit('copy', row.account.id)">
                        Code kopieren
                    </NcButton>
                </div>
            </li>
        </ul>
        <p id="passwords-otp-ap3-feedback" class="passwords-otp-feedback" role="status" aria-live="polite">{{ feedback }}</p>
    </section>
</template>
