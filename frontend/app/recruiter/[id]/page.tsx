'use client';
import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import AppBar from '@/components/AppBar';
import CredentialBadge from '@/components/CredentialBadge';
import VerifyScore from '@/components/VerifyScore';
import MeetScheduler from '@/components/MeetScheduler';
import { getToken, getRole, recruiterCandidate } from '@/lib/api';

type FW = { item_id: string; company_id: string; claim: string; contradicts: string };
type Segment = { t: number; type: string; severity: number; note: string };
type Proctoring = {
  integrity_confidence: number; risk_score: number; camera_available: boolean;
  flagged_segments: Segment[]; counts: Record<string, number>;
};
type Hist = {
  session_id: string; item_id: string; company_id: string; domain: string; level: string;
  type: string; proctored: boolean; verify_score: number; calibration: number;
  fluent_wrongness_count: number; graded_by: string; completed_at: string | null;
};
type Detail = {
  user_id: number; name: string; email: string;
  verify_score: number; verify_best: number; detection: number; explanation_quality: number;
  calibration: number; coverage_required: number; fluent_wrongness_total: number;
  items_attempted: number; sessions: number; domains: string[]; top_domain: string | null;
  companies: string[]; credential: 'verified' | 'developing' | 'unverified'; verified: boolean;
  credential_basis: string; fluent_wrongness_record: FW[]; history: Hist[]; last_active: string | null;
  proctoring: Proctoring | null;
};

const SEGMENT_LABEL: Record<string, string> = {
  tab_hidden: 'Left the interview tab', focus_loss: 'Window lost focus',
  paste: 'Pasted text', copy: 'Copied from the page', context_menu: 'Right-click menu',
  no_face: 'Face not visible', multiple_faces: 'Multiple people in frame',
};
const COUNT_LABEL: Record<string, string> = {
  tab_hidden: 'Tab switches', focus_loss: 'Focus losses', paste: 'Pastes',
  copy: 'Copies', multiple_faces: 'Multiple people', no_face: 'Face not visible',
  context_menu: 'Right-clicks',
};
const COUNT_ORDER = ['tab_hidden', 'paste', 'multiple_faces', 'no_face', 'focus_loss', 'copy', 'context_menu'];

const DOMAIN_LABEL: Record<string, string> = {
  core_se: 'Core SE', database: 'Database', web: 'Web', qa: 'QA', ml: 'AI/ML',
};
const fmt = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '—');
const mmss = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

export default function CandidateDetailPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<Detail | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    const role = getRole();
    if (role !== 'recruiter' && role !== 'company') { router.push('/practice'); return; }
    recruiterCandidate(id).then(setD).catch((e) => setErr(e.message || 'Not found'));
  }, [id, router]);

  if (err) return (
    <main className="min-h-screen"><AppBar />
      <div className="wrap py-10"><p className="text-brand">{err}</p>
        <button onClick={() => router.push('/recruiter')} className="btn-ghost mt-4">Back to pool</button>
      </div>
    </main>
  );
  if (!d) return <main className="min-h-screen"><AppBar /><div className="wrap py-10 text-muted">Loading…</div></main>;

  return (
    <main className="min-h-screen">
      <AppBar />
      <div className="wrap py-8">
        <button onClick={() => router.push('/recruiter')} className="text-sm text-muted hover:text-ink">← Candidate pool</button>

        {/* credential card */}
        <div className="panel mt-4 p-6 sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="font-serif text-3xl">{d.name}</h1>
                <CredentialBadge level={d.credential} />
              </div>
              <p className="mt-1 text-sm text-muted">{d.email}</p>
              <p className="mt-4 max-w-md text-sm text-ink">{d.credential_basis}</p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted">
                <span className="rounded-pill bg-white px-2.5 py-0.5">{d.items_attempted} items</span>
                <span className="rounded-pill bg-white px-2.5 py-0.5">best {d.verify_best}</span>
                {d.domains.map((dm) => (
                  <span key={dm} className="rounded-pill bg-white px-2.5 py-0.5">{DOMAIN_LABEL[dm] ?? dm}</span>
                ))}
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-muted">Verify score</p>
              <VerifyScore score={d.verify_score} size="lg" />
            </div>
          </div>
        </div>

        {/* invite to a Google Meet */}
        <MeetScheduler name={d.name} email={d.email} />

        {/* breakdown */}
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <Bar label="Detection" hint="Spotted the real fault" value={d.detection} />
          <Bar label="Explanation" hint="How clearly they reasoned" value={d.explanation_quality} />
          <Bar label="Calibration" hint="Knew when to trust the code" value={d.calibration} />
        </div>
        {d.explanation_quality - d.calibration >= 20 && (
          <p className="mt-3 text-sm text-[#C8352B]">
            Explains well but calibration lags — a sign of confident wrongness. Read the flagged claims below before shortlisting.
          </p>
        )}

        {/* proctoring integrity — only on proctored interviews */}
        {d.proctoring && (() => {
          const p = d.proctoring!;
          const integrity = Math.round(p.integrity_confidence * 100);
          const tone = integrity >= 80 ? 'text-ink' : integrity >= 55 ? 'text-brand' : 'text-[#C8352B]';
          return (
            <section className="mt-8">
              <h2 className="font-serif text-xl">Interview integrity</h2>
              <div className="mt-3 panel flex flex-wrap items-center justify-between gap-4 p-5">
                <div>
                  <p className="text-sm text-muted">Integrity confidence</p>
                  <p className={`font-serif text-4xl leading-none ${tone}`}>{integrity}<span className="text-xl">%</span></p>
                  <p className="mt-1 text-xs text-muted">
                    {p.camera_available ? 'Camera + event monitoring' : 'Event monitoring only (camera off)'}
                    {' · '}{p.flagged_segments.length} flagged moment{p.flagged_segments.length === 1 ? '' : 's'}
                    {' · '}risk {p.risk_score}/100
                  </p>
                </div>
              </div>
              {/* per-incident counts — how many times each thing happened */}
              {COUNT_ORDER.some((k) => (p.counts?.[k] ?? 0) > 0) && (
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {COUNT_ORDER.filter((k) => (p.counts?.[k] ?? 0) > 0).map((k) => (
                    <div key={k} className="rounded-xl border border-line bg-white p-3">
                      <p className="font-serif text-2xl leading-none text-ink">{p.counts[k]}</p>
                      <p className="mt-1 text-xs text-muted">{COUNT_LABEL[k] ?? k}</p>
                    </div>
                  ))}
                </div>
              )}
              {p.flagged_segments.length > 0 && (
                <ul className="mt-3 space-y-2">
                  {p.flagged_segments.map((seg, i) => (
                    <li key={i} className="flex items-center justify-between rounded-xl border border-line bg-white px-4 py-2.5 text-sm">
                      <span className="text-ink">{SEGMENT_LABEL[seg.type] ?? seg.note ?? seg.type}</span>
                      <span className="font-mono text-xs text-muted">{mmss(seg.t)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          );
        })()}

        {/* fluent-wrongness record — the signal that matters most */}
        <section className="mt-8">
          <h2 className="font-serif text-xl">Confidently-wrong claims</h2>
          {d.fluent_wrongness_record.length === 0 ? (
            <p className="mt-2 rounded-2xl border border-line bg-sand p-5 text-sm text-ink">
              None. Across {d.items_attempted} item{d.items_attempted === 1 ? '' : 's'}, this candidate never
              asserted something the code contradicts. That restraint is what the verified credential rewards.
            </p>
          ) : (
            <div className="mt-3 space-y-3">
              {d.fluent_wrongness_record.map((f, i) => (
                <div key={i} className="rounded-2xl border border-[#EFC9C3] bg-[#FBECEA] p-5">
                  <p className="text-xs uppercase tracking-wide text-[#C8352B]">{f.company_id} · {f.item_id}</p>
                  <p className="mt-1 text-sm text-ink">Claimed: <span className="italic">{f.claim}</span></p>
                  <p className="mt-1 text-sm text-muted">The code says: {f.contradicts}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* session history */}
        <section className="mt-8">
          <h2 className="font-serif text-xl">Session history</h2>
          <div className="mt-3 overflow-hidden rounded-2xl border border-line">
            <div className="hidden grid-cols-[1fr_1fr_0.7fr_0.8fr_0.9fr_0.8fr] gap-2 bg-sand px-4 py-2.5 text-xs uppercase tracking-wide text-muted sm:grid">
              <span>Item</span><span>Company</span><span>Verify</span><span>Calib.</span><span>Flags</span><span className="text-right">Date</span>
            </div>
            <ul className="divide-y divide-line bg-white">
              {d.history.map((h) => (
                <li key={h.session_id}
                    className="px-4 py-3 text-sm sm:grid sm:grid-cols-[1fr_1fr_0.7fr_0.8fr_0.9fr_0.8fr] sm:items-center sm:gap-2">
                  <span className="font-medium text-ink">
                    {h.item_id} <span className="text-xs font-normal text-muted">{DOMAIN_LABEL[h.domain] ?? h.domain} · {h.level}</span>
                  </span>
                  <span className="text-muted">{h.company_id}</span>
                  <span className={h.verify_score >= 75 ? 'text-ink' : h.verify_score >= 50 ? 'text-brand' : 'text-[#C8352B]'}>{h.verify_score}</span>
                  <span className="text-ink">{h.calibration}</span>
                  <span>
                    {h.fluent_wrongness_count > 0
                      ? <span className="text-[#C8352B]">{h.fluent_wrongness_count}</span>
                      : <span className="text-muted">—</span>}
                  </span>
                  <span className="text-right text-muted">{fmt(h.completed_at)}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* explainer */}
        <div className="mt-8 rounded-2xl border border-ink bg-ink p-6 text-paper">
          <p className="font-serif text-lg">What “verified” means</p>
          <p className="mt-2 text-sm text-paper/80">
            A candidate is verified when they score 70+ on average across at least two items and never make a
            confidently-wrong claim. The credential isn’t about sounding fluent — it’s proof they can tell when
            AI-written code is actually wrong. That’s the signal a résumé can’t give you.
          </p>
        </div>
      </div>
    </main>
  );
}

function Bar({ label, hint, value }: { label: string; hint: string; value: number }) {
  const tone = value >= 75 ? 'bg-ink' : value >= 50 ? 'bg-brand' : 'bg-[#C8352B]';
  return (
    <div className="lift panel p-5">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-medium text-ink">{label}</p>
        <p className="font-serif text-2xl">{value}</p>
      </div>
      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-pill bg-white">
        <div className={`h-full rounded-pill ${tone}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
      <p className="mt-2 text-xs text-muted">{hint}</p>
    </div>
  );
}
