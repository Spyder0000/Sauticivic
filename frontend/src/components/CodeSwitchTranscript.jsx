import React from 'react';
import { tagCodeSwitch } from '../lib/codeswitch';

// Word tint by language. Text colours are chosen for contrast on white/warm
// surfaces (gold uses its deeper shade so small serif stays legible).
const TINT = {
  en: 'text-ink',
  pidgin: 'text-palm',
  yoruba: 'text-gold-deep',
};

const LEGEND = [
  ['English', 'bg-ink'],
  ['Pidgin', 'bg-palm'],
  ['Yoruba', 'bg-gold'],
];

export function LangLegend({ className = '' }) {
  return (
    <div className={`flex flex-wrap items-center gap-x-3.5 gap-y-1.5 ${className}`}>
      <span className="text-[10px] font-mono uppercase tracking-[0.14em] text-muted/80">
        languages
      </span>
      {LEGEND.map(([label, dot]) => (
        <span key={label} className="inline-flex items-center gap-1.5 text-[11px] font-medium text-muted">
          <span className={`w-2 h-2 rounded-full ${dot}`} />
          {label}
        </span>
      ))}
    </div>
  );
}

// Renders a transcript as human speech: Fraunces serif, each word coloured by
// its language so the code-switch is visible rather than flattened. `reveal`
// fades words in left-to-right for a "being transcribed" feel (disabled under
// reduced motion by the global CSS guard).
export default function CodeSwitchTranscript({
  text,
  reveal = false,
  className = 'text-lg leading-relaxed',
}) {
  const tokens = tagCodeSwitch(text || '');
  let wordIndex = -1;

  return (
    <p className={`font-serif italic text-ink/90 ${className}`}>
      {tokens.map((t, i) => {
        if (t.lang === null) return <span key={i}>{t.text}</span>;
        wordIndex += 1;
        return (
          <span
            key={i}
            className={`${TINT[t.lang] || 'text-ink'} ${reveal ? 'animate-wordreveal' : ''}`}
            style={reveal ? { animationDelay: `${Math.min(wordIndex * 55, 2600)}ms` } : undefined}
          >
            {t.text}
          </span>
        );
      })}
    </p>
  );
}
