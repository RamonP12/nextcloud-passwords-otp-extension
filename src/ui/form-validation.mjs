/** Keep native form constraints and present their messages in the app locale. */
export function localizeInvalidField({target}, t) {
    const validity = target.validity;
    if (validity.valueMissing) target.setCustomValidity(t('required'));
    else if (validity.tooShort) target.setCustomValidity(t('too-short', {count: target.minLength}));
    else if (validity.tooLong) target.setCustomValidity(t('too-long', {count: target.maxLength}));
}

export function clearFieldValidation({target}) {
    target.setCustomValidity?.('');
}
