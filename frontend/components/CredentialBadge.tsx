'use client';

const STYLE: Record<string, string> = {
  verified: 'bg-ink text-paper',
  developing: 'bg-sand text-ink border border-line',
  unverified: 'bg-transparent text-muted border border-line',
};
const LABEL: Record<string, string> = {
  verified: 'Verified', developing: 'Developing', unverified: 'Unverified',
};

export default function CredentialBadge({ level }: { level: string }) {
  return (
    <span className={`inline-flex items-center rounded-pill px-3 py-1 text-xs font-medium ${STYLE[level] ?? STYLE.unverified}`}>
      {level === 'verified' && <span className="mr-1">✓</span>}
      {LABEL[level] ?? 'Unverified'}
    </span>
  );
}
