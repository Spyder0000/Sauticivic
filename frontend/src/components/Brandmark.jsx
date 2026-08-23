import React from 'react';

// The brand mark is the product itself: a voice. Five bars of a waveform,
// centred on the baseline. Colour comes from `currentColor` so it can sit on
// the dark sidebar (mint) or on paper (palm).
export default function Brandmark({ className = 'w-6 h-6' }) {
  const bars = [
    { x: 1.6, h: 4.5 },
    { x: 6.2, h: 8.5 },
    { x: 10.8, h: 11 },
    { x: 15.4, h: 6.5 },
    { x: 20, h: 3.5 },
  ];
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      {bars.map(({ x, h }, i) => (
        <rect
          key={i}
          x={x}
          y={12 - h}
          width="2.4"
          height={h * 2}
          rx="1.2"
          fill="currentColor"
          opacity={i === 2 ? 1 : 0.82}
        />
      ))}
    </svg>
  );
}
