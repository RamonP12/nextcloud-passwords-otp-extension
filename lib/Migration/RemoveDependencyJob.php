<?php

declare(strict_types=1);
namespace OCA\PasswordsOtp\Migration;

use OCA\PasswordsOtp\BackgroundJob\CheckPasswordsDependency;
use OCP\BackgroundJob\IJobList;
use OCP\Migration\IOutput;
use OCP\Migration\IRepairStep;

/** Nextcloud runs uninstall repair steps on disable, before app files disappear. */
final class RemoveDependencyJob implements IRepairStep {
    public function __construct(private IJobList $jobs) {}

    public function getName(): string {
        return 'Remove the Passwords OTP dependency job';
    }

    public function run(IOutput $output): void {
        $this->jobs->remove(CheckPasswordsDependency::class);
    }
}
