<?php

declare(strict_types=1);
namespace OCA\PasswordsOtp\Listener;

use OCA\PasswordsOtp\AppInfo\Application;
use OCA\PasswordsOtp\BackgroundJob\CheckPasswordsDependency;
use OCA\PasswordsOtp\Service\PasswordsDependency;
use OCP\App\Events\AppDisableEvent;
use OCP\App\Events\AppEnableEvent;
use OCP\App\Events\AppUpdateEvent;
use OCP\BackgroundJob\IJobList;
use OCP\EventDispatcher\Event;
use OCP\EventDispatcher\IEventListener;

/** @implements IEventListener<AppDisableEvent|AppEnableEvent|AppUpdateEvent> */
final class PasswordsLifecycleListener implements IEventListener {
    public function __construct(private PasswordsDependency $dependency, private IJobList $jobs) {}

    public function handle(Event $event): void {
        if (!$event instanceof AppDisableEvent && !$event instanceof AppEnableEvent
                && !$event instanceof AppUpdateEvent) return;
        $appId = $event->getAppId();
        if ($event instanceof AppEnableEvent && $appId === Application::APP_ID) {
            // Nextcloud emits this event after writing enabled=yes/groups. Undo
            // that write before reporting the dependency failure to UI/occ.
            $reason = $this->dependency->enforce();
            if ($reason !== null) throw new \RuntimeException(PasswordsDependency::message($reason));
            // IJobList::add is idempotent. Also restore the job for direct public
            // enableApp calls after a disable removed it via the uninstall step.
            $this->jobs->add(CheckPasswordsDependency::class);
            return;
        }
        if ($appId === PasswordsDependency::APP_ID
                || ($event instanceof AppUpdateEvent && $appId === Application::APP_ID)) {
            if ($this->dependency->enforce() !== null) {
                // upgradeApp schedules metadata jobs after running migrations;
                // remove a re-added job when the migration already disabled OTP.
                $this->jobs->remove(CheckPasswordsDependency::class);
            }
        }
    }
}
