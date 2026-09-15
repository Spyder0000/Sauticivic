import assert from 'node:assert/strict';
import test from 'node:test';

import { getClarificationState } from './clarificationState.js';


test('treats an explicit human-review outcome as terminal', () => {
  assert.deepEqual(getClarificationState({ status: 'human_review', rounds_remaining: 0 }), {
    isEmergency: false,
    isHumanReview: true,
    canClarify: false,
  });
});


test('defensively stops clarification when no rounds remain', () => {
  assert.deepEqual(getClarificationState({ status: 'needs_clarification', rounds_remaining: 0 }), {
    isEmergency: false,
    isHumanReview: true,
    canClarify: false,
  });
});


test('allows clarification while rounds remain', () => {
  assert.deepEqual(getClarificationState({ status: 'needs_clarification', rounds_remaining: 2 }), {
    isEmergency: false,
    isHumanReview: false,
    canClarify: true,
  });
});
