<?php

declare(strict_types=1);
namespace OCA\PasswordsOtp\Controller;
use OCA\PasswordsOtp\AppInfo\Application;
use OCA\PasswordsOtp\Service\PasswordsAuthAdapter;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\Attribute\NoAdminRequired;
use OCP\AppFramework\Http\Attribute\NoCSRFRequired;
use OCP\AppFramework\Http\Attribute\UseSession;
use OCP\AppFramework\Http\JSONResponse;
use OCP\AppFramework\Http\TemplateResponse;
use OCP\AppFramework\Services\IInitialState;
use OCP\IRequest;
use OCP\ISession;
use OCP\IURLGenerator;
use OCP\Util;
use Throwable;
final class PageController extends Controller {
    public function __construct(IRequest $request, private IInitialState $initialState,
        private IURLGenerator $urlGenerator, private PasswordsAuthAdapter $authAdapter,
        private ISession $nextcloudSession) { parent::__construct(Application::APP_ID, $request); }
    #[NoAdminRequired]
    #[NoCSRFRequired]
    #[UseSession]
    public function index(): TemplateResponse {
        $state = ['status' => 'unavailable', 'reason' => 'https-required'];
        if ($this->request->getServerProtocol() === 'https') {
            try {
                $state = ['status' => 'ready',
                    'bootstrapUrl' => $this->urlGenerator->linkToRoute('passwords_otp.page.bootstrap'),
                    'sessionStatusUrl' => $this->urlGenerator->linkToRoute('passwords_otp.page.sessionStatus'),
                    'sessionFingerprint' => $this->currentSessionFingerprint()];
            } catch (Throwable) { $state = ['status' => 'unavailable', 'reason' => 'integration-unavailable']; }
        }
        $this->initialState->provideInitialState('ap1', $state);
        Util::addScript(Application::APP_ID, 'app-100');
        Util::addStyle(Application::APP_ID, 'app-100');
        $response = new TemplateResponse(Application::APP_ID, 'main');
        // Required by the unmodified upstream libsodium/PWDv1r1 implementation.
        $response->getContentSecurityPolicy()->allowEvalWasm(true);
        $response->addHeader('Cache-Control', 'private, no-store, max-age=0');
        $response->addHeader('Pragma', 'no-cache');
        $response->addHeader('Referrer-Policy', 'no-referrer');
        return $response;
    }
    private function currentSessionFingerprint(): string {
        $uid = $this->authAdapter->currentValidUid();
        $id = $this->nextcloudSession->getId();
        if ($uid === null || $id === '') throw new \RuntimeException('No active session');
        return hash('sha256', $id . "\0" . $uid);
    }
    private function json(array $data, int $status = 200): JSONResponse {
        $response = new JSONResponse($data, $status);
        $response->addHeader('Cache-Control', 'private, no-store, max-age=0');
        $response->addHeader('Pragma', 'no-cache');
        $response->addHeader('Referrer-Policy', 'no-referrer');
        $response->addHeader('X-Content-Type-Options', 'nosniff');
        return $response;
    }
    #[NoAdminRequired]
    #[NoCSRFRequired]
    #[UseSession]
    public function sessionStatus(): JSONResponse {
        try {
            if ($this->request->getServerProtocol() !== 'https') throw new \RuntimeException('HTTPS required');
            return $this->json(['authenticated' => true, 'sessionFingerprint' => $this->currentSessionFingerprint()]);
        } catch (Throwable) { return $this->json(['authenticated' => false], 403); }
    }
    /** No NoCSRFRequired/PublicPage attribute: Nextcloud login and CSRF middleware remain mandatory. */
    #[NoAdminRequired]
    #[UseSession]
    public function bootstrap(): JSONResponse {
        try {
            if ($this->request->getServerProtocol() !== 'https') return $this->json(['status' => 'unavailable'], 403);
            $expected = $this->request->getHeader('X-Passwords-OTP-Session');
            $current = $this->currentSessionFingerprint();
            if (!is_string($expected) || preg_match('/\A[0-9a-f]{64}\z/', $expected) !== 1
                    || !hash_equals($current, $expected)) return $this->json(['status' => 'unavailable'], 403);
            $credentials = $this->authAdapter->acquire();
            if ($credentials['status'] !== 'ready') return $this->json($credentials, 403);
            if (!hash_equals($current, $this->currentSessionFingerprint())) return $this->json(['status' => 'unavailable'], 403);
            return $this->json(['status' => 'ready', 'login' => $credentials['login'], 'token' => $credentials['token'],
                'sessionFingerprint' => $current,
                'sessionRequestUrl' => $this->urlGenerator->linkToRoute('passwords.session_api.request'),
                'passwordListUrl' => $this->urlGenerator->linkToRoute('passwords.password_api.list'),
                'sessionOpenUrl' => $this->urlGenerator->linkToRoute('passwords.session_api.open')]);
        } catch (Throwable) { return $this->json(['status' => 'unavailable', 'reason' => 'integration-unavailable'], 403); }
    }
}
