// Verified against docs/BENCHMARK_REPORT.md and benchmark result artifacts.
// These are benchmark results, never service-level or production guarantees.
export const benchmarkResults = [
  { label: 'Sahara Tier A-MSV', value: '0/21', detail: 'polarity inversions' },
  { label: 'Gemini', value: '10/21', detail: 'polarity inversions' },
  { label: 'Deepgram', value: '10/21', detail: 'polarity inversions' },
  { label: 'Whisper', value: '11/21', detail: 'polarity inversions' },
  { label: 'v19 artifact corruption', value: '0/30', detail: 'Tier A clips' },
  { label: 'Adversarial harm avoidance', value: '10/10', detail: 'trap cases' },
];
