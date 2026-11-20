<?php

declare(strict_types=1);
namespace OCA\PasswordsOtp\BackgroundJob;

use OCP\BackgroundJob\IJobList;
use OCP\BackgroundJob\Job;

/** Retire any persisted periodic check registered by a previous release. */
final class CheckPasswordsDependency extends Job {
    public function start(IJobList $jobList): void {
        $jobList->remove(self::class);
    }

    protected function run($argument): void {}
}
