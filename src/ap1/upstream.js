import PasswordsClient from 'passwords-client';
import {ApiRequest} from 'passwords-client/http';
import sodium from 'libsodium-wrappers-sumo';
import {assertOtpApiOperation} from '../ap12/api-policy.mjs';
import {boundedRequest, validateApiTarget, NetworkFault} from './network.mjs';
/** Uses the pinned upstream client; deadline includes the response body, not only headers. */
export class LockedApiRequest extends ApiRequest {
    #signal = null;
    #sent = false;
    async send() {
        if (this.#sent) throw new NetworkFault('request-reuse-denied');
        this.#sent = true;
        try {
            return await boundedRequest(this._api, async signal => {
                this.#signal = signal;
                return super.send();
            });
        } finally {
            this.#signal = null;
            this._data = null;
        }
    }
    _getRequestOptions() {
        return {...super._getRequestOptions(), credentials: 'omit', redirect: 'error',
            cache: 'no-store', referrerPolicy: 'no-referrer', signal: this.#signal};
    }
    async _executeRequest(url, options) {
        const target = validateApiTarget(url, this._api.getServer().getApiUrl(), window.location.href);
        assertOtpApiOperation(target.route, options?.method || 'GET', this._api);
        if (!this.#signal || this.#signal.aborted) throw new NetworkFault('request-aborted');
        const response = await super._executeRequest(target.href, {
            ...options, credentials: 'omit', redirect: 'error', cache: 'no-store',
            referrerPolicy: 'no-referrer', signal: this.#signal
        });
        if (!this.#signal || this.#signal.aborted) throw new NetworkFault('request-aborted');
        return response;
    }
}
export const sodiumReady = () => sodium.ready;
export function createClient(configuration) {
    return new PasswordsClient({baseUrl: configuration.baseUrl, user: configuration.user,
        token: configuration.token}, {}, {'network.request': LockedApiRequest});
}
