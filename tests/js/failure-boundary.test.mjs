import test from 'node:test';
import assert from 'node:assert/strict';
import {createUiFailureBoundary} from '../../src/ui/failure-boundary.mjs';

test('Failure stops a registered controller before synchronous DOM erasure', () => {
    const events = [];
    const boundary = createUiFailureBoundary(() => events.push('clear'));
    boundary.register(() => events.push('stop'));
    boundary.fail();
    assert.equal(boundary.failed, true);
    assert.deepEqual(events, ['stop', 'clear']);
    boundary.fail();
    assert.deepEqual(events, ['stop', 'clear', 'clear'], 'repeat errors scrub again without invoking stop twice');
});

test('A controller registered after an early mount failure is stopped before startup', () => {
    const events = [];
    let ended = false;
    const boundary = createUiFailureBoundary(() => events.push('clear'));
    boundary.fail();
    boundary.register(() => { ended = true; events.push('stop'); });
    // Models the later mounted hook: start may only run while not terminated.
    if (!ended) events.push('credential-bootstrap');
    assert.deepEqual(events, ['clear', 'stop', 'clear']);
    assert.equal(boundary.failed, true);
});

test('Recursive rendering errors do not create an infinite failure-handler loop', () => {
    const events = [];
    const boundary = createUiFailureBoundary(() => { events.push('clear'); boundary.fail(); });
    boundary.register(() => { events.push('stop'); boundary.fail(); });
    boundary.fail();
    assert.deepEqual(events, ['stop', 'clear']);
    assert.equal(boundary.failed, true);
});

test('A throwing controller cleanup cannot prevent erasure or escape sensitive exception details', () => {
    let erased = false;
    const boundary = createUiFailureBoundary(() => { erased = true; });
    boundary.register(() => { throw new Error('SYNTHETIC-PRIVATE-DETAIL'); });
    assert.doesNotThrow(boundary.fail);
    assert.equal(erased, true);
    assert.equal(boundary.failed, true);
});

test('A broken erasure callback still leaves a stopped controller and a terminal boundary', () => {
    let stopped = false;
    const boundary = createUiFailureBoundary(() => { throw new Error('synthetic DOM failure'); });
    boundary.register(() => { stopped = true; });
    assert.doesNotThrow(boundary.fail);
    assert.equal(stopped, true);
    assert.equal(boundary.failed, true);
});

test('Invalid controller registration fails closed', () => {
    let cleared = 0;
    const boundary = createUiFailureBoundary(() => cleared++);
    boundary.register(undefined);
    assert.equal(boundary.failed, true);
    assert.equal(cleared, 1);
});
