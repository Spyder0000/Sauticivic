// Code-switch tagger — demo-scoped, keyword-based.
//
// SautiCivic's thesis is that code-switching is *signal, not noise*: a citizen
// who slips from English into Pidgin or Yoruba mid-sentence is conveying
// meaning, not creating a transcription problem. The backend keeps that content
// rather than normalising it away; this helper is the front-end's small echo of
// that idea — it *labels* each word by the language it came from so the UI can
// show the switch instead of flattening it.
//
// This is deliberately not a linguistic model. It's a lexicon big enough to read
// honestly on real Nigerian code-switched input (and on the three demo prompts),
// with a little context for the genuinely ambiguous tokens.

const YORUBA = new Set([
  'kaaro', 'kaabo', 'ku', 'mo', 'fe', 'fẹ', 'ni', 'ti', 'wa', 'jo', 'jọ',
  'ejo', 'ejọ', 'omo', 'ọmọ', 'ile', 'ilé', 'omi', 'owo', 'owó', 'oro', 'ọrọ',
  'pele', 'pẹlẹ', 'ẹ', 'yin', 'won', 'wọn', 'ba', 'se', 'ṣe', 'jọwọ', 'jowo',
]);

const PIDGIN = new Set([
  'dey', 'don', 'wey', 'wetin', 'abeg', 'na', 'sabi', 'comot', 'make', 'am',
  'sef', 'wahala', 'pikin', 'waka', 'chop', 'vex', 'fit', 'tey', 'biko',
  'plenty', 'sha', 'shele', 'yawa', 'gan', 'abi', 'oga', 'pack',
]);

// Pidgin auxiliaries — used to disambiguate the bare pronoun "e" ("e don spoil")
const PIDGIN_AUX = new Set(['don', 'dey', 'go', 'fit', 'no', 'sef', 'never']);

function classifyToken(word, prevWord, nextWord) {
  const w = word.toLowerCase();
  if (!w) return 'en';

  // "E kaaro / E kaabo / E ku ..." — Yoruba greeting particle
  if (w === 'e' && YORUBA.has((nextWord || '').toLowerCase())) return 'yoruba';
  // "e don / e dey / e go ..." — Pidgin pronoun "it"
  if (w === 'e' && PIDGIN_AUX.has((nextWord || '').toLowerCase())) return 'pidgin';

  if (YORUBA.has(w)) return 'yoruba';
  if (PIDGIN.has(w)) return 'pidgin';

  // "report say ..." — "say" as a complementiser is Pidgin, not the English verb
  if (w === 'say' && ['report', 'tell', 'talk', 'hear', 'know', 'sure', 'mean']
    .includes((prevWord || '').toLowerCase())) return 'pidgin';
  // "for Alagomeji" — "for" as a locative before a place name is Pidgin
  if (w === 'for' && nextWord && /^[A-ZÀ-Ý]/.test(nextWord)) return 'pidgin';

  return 'en';
}

// Returns an ordered list of { text, lang } segments covering the whole string.
// Whitespace/punctuation segments carry lang === null so callers can render them
// without a tint. Words carry lang ∈ {'en','pidgin','yoruba'}.
export function tagCodeSwitch(text) {
  if (!text) return [];
  const tokens = text.match(/(\s+|[^\s\w'’]+|[\w'’À-ÿ]+)/g) || [];
  const words = tokens.filter((t) => /[\w'’À-ÿ]/.test(t));
  let wi = -1;
  return tokens.map((tok) => {
    if (!/[\w'’À-ÿ]/.test(tok)) return { text: tok, lang: null };
    wi += 1;
    return { text: tok, lang: classifyToken(tok, words[wi - 1], words[wi + 1]) };
  });
}

// Human-readable list of the languages actually present, in a stable order.
export function detectedLanguages(text) {
  const present = new Set(tagCodeSwitch(text).map((t) => t.lang).filter(Boolean));
  const LABELS = [['en', 'English'], ['pidgin', 'Pidgin'], ['yoruba', 'Yoruba']];
  return LABELS.filter(([k]) => present.has(k)).map(([, label]) => label);
}
