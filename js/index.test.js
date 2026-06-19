import assert from 'node:assert/strict';
import test from 'node:test';
import { parseUri } from './index.js';

test('parses resource URI', () => {
  assert.deepEqual(parseUri('device://device-01/led/command/set'), {
    kind: 'command',
    operation: 'set',
    raw: 'device://device-01/led/command/set',
    resource: 'led',
    scheme: 'device',
    target: 'device-01',
  });
});

test('parses short process URI', () => {
  assert.equal(parseUri('process://bridge/command/smoke').resource, 'process');
});

test('rejects invalid URI', () => {
  assert.throws(() => parseUri('not-a-uri'), /Invalid URI/);
});
