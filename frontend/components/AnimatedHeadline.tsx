'use client';

// Letters load with a quiet flicker of blue, then settle to ink over ~2.5s.
// Deterministic colors (no hydration mismatch); only blue + ink, per the brand palette.
// A '|' in `text` forces a hard line break (so the headline reads on two lines).
const PALETTE = ['#0A66F0', '#111317', '#111317', '#0A66F0', '#111317', '#111317', '#0A66F0', '#111317'];

export default function AnimatedHeadline({ text, className = '' }: { text: string; className?: string }) {
  const lines = text.split('|');
  let colorIdx = 0;
  return (
    <h1 className={`hero-line ${className}`} aria-label={text.replace(/\|/g, ' ')}>
      {lines.map((line, li) => (
        <span key={li} className="block" aria-hidden="true">
          {line.trim().split(' ').map((word, wi) => (
            <span key={wi} className="inline-block whitespace-nowrap" style={{ marginRight: '0.26em' }}>
              {word.split('').map((ch, ci) => {
                const c = PALETTE[colorIdx % PALETTE.length];
                const d = colorIdx * 28;
                colorIdx++;
                return (
                  <span key={ci} className="hero-letter" style={{ ['--c' as string]: c, ['--d' as string]: `${d}ms` }}>
                    {ch}
                  </span>
                );
              })}
            </span>
          ))}
        </span>
      ))}
    </h1>
  );
}
