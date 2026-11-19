<?php

declare(strict_types=1);
namespace OCA\PasswordsOtp\AppInfo;
use OCA\PasswordsOtp\Listener\PasswordsLifecycleListener;
use OCA\PasswordsOtp\Service\PasswordsDependency;
use OCP\App\Events\AppDisableEvent;
use OCP\App\Events\AppEnableEvent;
use OCP\App\Events\AppUpdateEvent;
use OCP\AppFramework\App;
use OCP\AppFramework\Bootstrap\IBootContext;
use OCP\AppFramework\Bootstrap\IBootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;
final class Application extends App implements IBootstrap {
    public const APP_ID = 'passwords_otp';
    public function __construct(array $urlParams = []) { parent::__construct(self::APP_ID, $urlParams); }
    public function register(IRegistrationContext $context): void {
        $context->registerEventListener(AppDisableEvent::class, PasswordsLifecycleListener::class);
        $context->registerEventListener(AppEnableEvent::class, PasswordsLifecycleListener::class);
        $context->registerEventListener(AppUpdateEvent::class, PasswordsLifecycleListener::class);
    }
    public function boot(IBootContext $context): void {
        $context->injectFn(static function (PasswordsDependency $dependency): void {
            $dependency->enforce();
        });
    }
}
