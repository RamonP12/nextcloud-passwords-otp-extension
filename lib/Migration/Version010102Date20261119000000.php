<?php

declare(strict_types=1);
namespace OCA\PasswordsOtp\Migration;

use Closure;
use OCA\PasswordsOtp\Service\PasswordsDependency;
use OCP\Migration\IOutput;
use OCP\Migration\SimpleMigrationStep;

/** Dependency registration guard. Creates no OTP table or schema change. */
final class Version010102Date20261119000000 extends SimpleMigrationStep {
    public function __construct(private PasswordsDependency $dependency) {}

    public function name(): string {
        return 'Verify the Passwords prerequisite';
    }

    public function changeSchema(IOutput $output, Closure $schemaClosure, array $options) {
        // Initial Nextcloud installations run schema-only migrations: pre/post
        // callbacks are skipped. Normal repair-step exceptions are swallowed.
        $this->dependency->checkInstallation();
        return null;
    }
}
