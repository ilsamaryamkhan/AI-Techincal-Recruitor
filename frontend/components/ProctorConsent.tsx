'use client';

export default function ProctorConsent({ onAccept, onCancel, busy }:
  { onAccept: () => void; onCancel: () => void; busy?: boolean }) {
  return (
    <div className="panel mx-auto max-w-xl p-6 sm:p-8">
      <p className="text-sm text-muted">Before you begin</p>
      <h2 className="mt-1 font-serif text-2xl">This interview is proctored</h2>
      <p className="mt-3 text-muted">
        To keep the result credible for the company, we monitor a few things during the interview:
      </p>
      <ul className="mt-4 space-y-2 text-sm text-ink">
        <li className="flex gap-2"><span aria-hidden>•</span> Your camera, to confirm you&apos;re present and that no one else is in frame.</li>
        <li className="flex gap-2"><span aria-hidden>•</span> Tab switches and when the window loses focus.</li>
        <li className="flex gap-2"><span aria-hidden>•</span> Pasting into the answer box.</li>
      </ul>
      <div className="mt-4 rounded-xl border border-line bg-white p-3 text-sm text-muted">
        No video is recorded or uploaded. Only the signals above — as counts and a timeline — are shared with the company.
        If you don&apos;t allow the camera, you can still continue with tab and paste monitoring only.
      </div>
      <div className="mt-6 flex items-center gap-3">
        <button className="btn-dark" onClick={onAccept} disabled={busy}>
          {busy ? 'Starting…' : 'I understand — begin interview'}
        </button>
        <button className="btn-ghost" onClick={onCancel} disabled={busy}>Cancel</button>
      </div>
    </div>
  );
}
