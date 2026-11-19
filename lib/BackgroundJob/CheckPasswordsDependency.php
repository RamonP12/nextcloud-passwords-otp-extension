<?php

declare(strict_types=1);
namespace OCA\PasswordsOtp\BackgroundJob;

use OCA\PasswordsOtp\Service\PasswordsDependency;
use OCP\AppFramework\Utility\ITimeFactory;
use OCP\BackgroundJob\TimedJob;

/** Fallback for removal with --keep-data/manual file deletion and missed events. */
final class CheckPasswordsDependency extends TimedJob {
    public function __construct(ITimeFactory $time, private PasswordsDependency $dependency) {
        parent::__construct($time);
        $this->setInterval(300);
        $this->setAllowParallelRuns(false);
    }

    protected function run($argument): void {
        $this->dependency->enforce();
    }
}
