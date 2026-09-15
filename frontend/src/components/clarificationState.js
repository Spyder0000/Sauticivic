export function getClarificationState(outcome) {
  const isEmergency = outcome?.status === 'emergency_recommendation';
  const isHumanReview = outcome?.status === 'human_review'
    || (outcome?.status === 'needs_clarification' && outcome?.rounds_remaining === 0);

  return {
    isEmergency,
    isHumanReview,
    canClarify: outcome?.status === 'needs_clarification' && !isHumanReview,
  };
}
