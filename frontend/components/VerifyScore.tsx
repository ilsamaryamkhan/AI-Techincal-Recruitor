'use client';

/** The headline comprehension score. Color encodes the band:
 *  strong (ink), passing (brand blue), weak (clay red). */
export default function VerifyScore({ score, size = 'md' }: { score: number; size?: 'md' | 'lg' }) {
  const tone = score >= 75 ? 'text-ink' : score >= 50 ? 'text-brand' : 'text-[#C8352B]';
  const cls = size === 'lg' ? 'font-serif text-6xl leading-none' : 'font-serif text-2xl leading-none';
  return <span className={`${cls} ${tone}`}>{score}</span>;
}
