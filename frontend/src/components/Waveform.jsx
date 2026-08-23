import React, { useMemo } from 'react';

// A row of vertical bars. `active` drives the live-capture animation; it falls
// back to a calm static profile when idle or when the reader prefers reduced
// motion (we check the media query in JS so the bars keep their real height
// instead of freezing mid-transform).
export default function Waveform({
  active = false,
  bars = 32,
  className = '',
  barClassName = 'bg-current',
  gap = 'gap-[3px]',
}) {
  const prefersReduced = useMemo(
    () => typeof window !== 'undefined'
      && window.matchMedia
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    [],
  );
  const animate = active && !prefersReduced;

  // A fixed, organic-looking height profile (0..1), tiled to `bars`.
  const profile = [0.30, 0.55, 0.78, 0.44, 0.92, 0.62, 1.0, 0.4, 0.72, 0.5,
    0.86, 0.34, 0.66, 0.5, 0.95, 0.3, 0.58, 0.8, 0.42, 0.7];

  return (
    <div className={`flex items-center ${gap} ${className}`} aria-hidden="true">
      {Array.from({ length: bars }).map((_, i) => {
        const h = profile[i % profile.length];
        return (
          <span
            key={i}
            className={`w-[3px] rounded-full origin-center ${barClassName} ${animate ? 'animate-equalize' : ''}`}
            style={{
              height: `${Math.round(h * 100)}%`,
              animationDelay: animate ? `${(i % profile.length) * 55}ms` : undefined,
            }}
          />
        );
      })}
    </div>
  );
}
