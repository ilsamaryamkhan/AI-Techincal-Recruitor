'use client';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import AppBar from '@/components/AppBar';
import CodePanel from '@/components/CodePanel';
import { getToken, getRole, startInterview, answerInterview, postProctor } from '@/lib/api';
import { useSpeech } from '@/lib/useSpeech';
import { useProctor } from '@/lib/useProctor';
import ProctorMonitor from '@/components/ProctorMonitor';
import ProctorConsent from '@/components/ProctorConsent';

type Item = {
  item_id: string; company_id: string; domain: string; level: string;
  mode: string; language: string; prompt: string;
  artifact: { files: { path: string; content: string }[] };
};
const DOMAIN_LABEL: Record<string, string> = { core_se: 'Core SE', database: 'Database' };
const ALERT_MSG: Record<string, string> = {
  tab_hidden: 'You left the interview tab — this was recorded.',
  focus_loss: 'The window lost focus — this was recorded.',
  paste: 'Pasting into your answer is recorded.',
  copy: 'Copying from the page is recorded.',
  multiple_faces: 'More than one person detected in frame.',
  no_face: 'Your face isn’t visible to the camera.',
  context_menu: 'Right-click menu opened — recorded.',
};

function mmss(s: number) {
  const m = Math.floor(s / 60), r = s % 60;
  return `${m}:${r.toString().padStart(2, '0')}`;
}

export default function InterviewPage() {
  const router = useRouter();
  const [phase, setPhase] = useState<'setup' | 'consent' | 'running' | 'done'>('setup');
  const [domain, setDomain] = useState('');
  const [level, setLevel] = useState('');
  const proctored = true; // live interviews are always proctored — not optional

  const [sid, setSid] = useState('');
  const [item, setItem] = useState<Item | null>(null);
  const [stage, setStage] = useState<'main' | 'followup'>('main');
  const [followup, setFollowup] = useState('');
  const [index, setIndex] = useState(0);
  const [total, setTotal] = useState(0);
  const [company, setCompany] = useState('');

  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [summary, setSummary] = useState<{ items: number; verify_score: number; company_id: string } | null>(null);

  const [secs, setSecs] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const { supported, listening, start: micStart, stop: micStop } =
    useSpeech((chunk) => setAnswer((a) => (a ? a + chunk : chunk)));
  const proctor = useProctor();

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    if (getRole() !== 'candidate') { router.push('/recruiter'); return; }
  }, [router]);

  // Proctoring lifecycle: start when the running screen (and its <video>) is up,
  // stop when leaving it. One effect so it survives React StrictMode's
  // mount→unmount→remount in dev (start/stop/start nets out to "started").
  useEffect(() => {
    if (phase !== 'running' || !proctored) return;
    proctor.start();
    return () => proctor.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, proctored]);

  // show a warning toast each time proctoring flags something
  useEffect(() => {
    if (!proctor.alert) return;
    setToast(ALERT_MSG[proctor.alert.type] ?? proctor.alert.note);
    const id = setTimeout(() => setToast(null), 3800);
    return () => clearTimeout(id);
  }, [proctor.alert]);

  // count-up timer, reset whenever a new item is served
  useEffect(() => {
    if (phase !== 'running') { if (timer.current) clearInterval(timer.current); return; }
    setSecs(0);
    timer.current = setInterval(() => setSecs((s) => s + 1), 1000);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [phase, index]);

  function begin() {
    setErr('');
    if (proctored) { setPhase('consent'); return; }
    startRun();
  }

  async function startRun() {
    setBusy(true); setErr('');
    try {
      const r = await startInterview({ domain: domain || undefined, level: level || undefined });
      setSid(r.session_id); setItem(r.item); setStage('main');
      setIndex(r.index); setTotal(r.total); setCompany(r.company_id);
      setAnswer(''); setPhase('running');
    } catch (e: any) { setErr(e.message || 'Could not start'); setPhase('setup'); }
    finally { setBusy(false); }
  }

  async function submit() {
    if (!answer.trim() || busy) return;
    if (listening) micStop();
    setBusy(true); setErr('');
    try {
      const r = await answerInterview(sid, answer);
      if (r.done) {
        if (proctored) {
          proctor.stop();
          try { await postProctor(sid, proctor.summary()); } catch { /* proctoring is best-effort */ }
        }
        setSummary(r.summary); setPhase('done'); return;
      }
      if (r.stage === 'followup') { setStage('followup'); setFollowup(r.followup); setAnswer(''); }
      else { setStage('main'); setItem(r.item); setIndex(r.index); setAnswer(''); }
    } catch (e: any) { setErr(e.message || 'Could not submit'); }
    finally { setBusy(false); }
  }

  // ---------- setup ----------
  if (phase === 'setup') {
    return (
      <main className="min-h-screen">
        <AppBar />
        <div className="wrap mx-auto max-w-xl py-12">
          <p className="text-sm text-muted">Live interview</p>
          <h1 className="font-serif text-4xl leading-tight">Start a proctored interview</h1>
          <p className="mt-3 text-muted">
            Three items, one at a time. You read AI-written code and explain it out loud or in writing.
            After each answer the interviewer asks one follow-up that reacts to what you said. You won&apos;t
            see scores as you go — your result goes to the company afterward.
          </p>
          <div className="panel mt-6 space-y-4 p-6">
            <div>
              <label className="text-sm font-medium text-ink">Domain</label>
              <select className="field mt-1.5" value={domain} onChange={(e) => setDomain(e.target.value)}>
                <option value="">Mixed (recommended)</option>
                <option value="core_se">Core SE</option>
                <option value="database">Database</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-ink">Level</label>
              <select className="field mt-1.5" value={level} onChange={(e) => setLevel(e.target.value)}>
                <option value="">Any</option>
                <option value="associate">Associate</option>
                <option value="engineer">Engineer</option>
                <option value="senior">Senior</option>
              </select>
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-line bg-white px-4 py-3 text-sm">
              <span aria-hidden>🔒</span>
              <span className="text-ink">This interview is proctored — camera presence and tab/paste monitoring are always on.</span>
            </div>
            {err && <p className="text-sm text-brand">{err}</p>}
            <button className="btn-dark w-full py-3 text-base" onClick={begin} disabled={busy}>
              {busy ? 'Starting…' : 'Continue'}
            </button>
          </div>
          <button onClick={() => router.push('/practice')} className="mt-5 text-sm text-muted hover:text-ink">
            ← Back to practice
          </button>
        </div>
      </main>
    );
  }

  // ---------- consent ----------
  if (phase === 'consent') {
    return (
      <main className="min-h-screen">
        <AppBar />
        <div className="wrap py-12">
          <ProctorConsent onAccept={startRun} onCancel={() => setPhase('setup')} busy={busy} />
          {err && <p className="mx-auto mt-3 max-w-xl text-sm text-brand">{err}</p>}
        </div>
      </main>
    );
  }

  // ---------- done ----------
  if (phase === 'done' && summary) {
    const tone = summary.verify_score >= 75 ? 'text-ink' : summary.verify_score >= 50 ? 'text-brand' : 'text-[#C8352B]';
    return (
      <main className="min-h-screen">
        <AppBar />
        <div className="wrap mx-auto max-w-xl py-16 text-center">
          <p className="text-sm text-muted">Interview complete</p>
          <p className={`mt-3 font-serif text-7xl leading-none ${tone}`}>{summary.verify_score}</p>
          <p className="mt-2 text-muted">your verify score</p>
          <p className="mt-6 text-ink">
            Thanks — you answered all {summary.items} items. Your result has been sent to{' '}
            <span className="font-medium">{summary.company_id}</span> for review.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <button onClick={() => router.push('/practice')} className="btn-dark">Back to practice</button>
            <button onClick={() => { setPhase('setup'); setSummary(null); }} className="btn-ghost">Take another</button>
          </div>
        </div>
      </main>
    );
  }

  // ---------- running ----------
  const code = item?.artifact.files[0]?.content ?? '';
  return (
    <main className="min-h-screen">
      <AppBar />
      {proctored && (
        <ProctorMonitor videoRef={proctor.videoRef} status={proctor.status}
                        cameraAvailable={proctor.cameraAvailable} flags={proctor.flags} risk={proctor.risk} />
      )}
      {toast && (
        <div className="fixed left-1/2 top-4 z-50 -translate-x-1/2">
          <div className="flex items-center gap-2 rounded-pill border border-[#EFC9C3] bg-[#FBECEA] px-4 py-2 text-sm font-medium text-[#C8352B] shadow-lg">
            <span aria-hidden>⚠</span> {toast}
          </div>
        </div>
      )}
      <div className="wrap py-6">
        {/* progress + timer */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <p className="text-sm text-muted">Item {index + 1} of {total}</p>
            <span className={`rounded-pill px-2.5 py-0.5 text-xs font-medium ${
              stage === 'followup' ? 'bg-ink text-paper' : 'bg-sand text-ink'}`}>
              {stage === 'followup' ? 'Follow-up' : 'Question'}
            </span>
          </div>
          <p className="font-mono text-sm text-muted tabular-nums">{mmss(secs)}</p>
        </div>
        <div className="mt-2 h-1 w-full overflow-hidden rounded-pill bg-sand">
          <div className="h-full rounded-pill bg-ink transition-all"
               style={{ width: `${(index / total) * 100 + (stage === 'followup' ? 50 / total : 0)}%` }} />
        </div>

        {item && (
          <div className="mt-5 flex flex-wrap items-center gap-2 text-sm text-muted">
            <span className="rounded-pill bg-sand px-2.5 py-0.5">{item.company_id}</span>
            <span className="rounded-pill bg-sand px-2.5 py-0.5">{DOMAIN_LABEL[item.domain] ?? item.domain}</span>
            <span className="rounded-pill bg-sand px-2.5 py-0.5">{item.level}</span>
          </div>
        )}

        {stage === 'main' ? (
          <h1 className="mt-4 font-serif text-2xl leading-snug">{item?.prompt}</h1>
        ) : (
          <div className="mt-4 rounded-2xl border border-ink bg-ink p-5 text-paper">
            <p className="text-sm text-paper/70">Interviewer follow-up</p>
            <p className="mt-1 font-serif text-xl">{followup}</p>
          </div>
        )}

        <div className="mt-5">
          <CodePanel code={code} language={item?.language ?? 'python'} />
        </div>

        <div className="mt-6">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-ink">
              {stage === 'followup' ? 'Your response' : 'Your explanation'}
            </label>
            {supported && (
              <button
                onClick={() => (listening ? micStop() : micStart())}
                className={`inline-flex items-center gap-1.5 rounded-pill border px-3 py-1 text-xs font-medium transition-colors ${
                  listening ? 'border-[#C8352B] bg-[#FBECEA] text-[#C8352B]' : 'border-line bg-white text-ink hover:bg-sand'}`}
              >
                <span className={`inline-block h-2 w-2 rounded-full ${listening ? 'animate-pulse bg-[#C8352B]' : 'bg-muted'}`} />
                {listening ? 'Listening… tap to stop' : 'Speak answer'}
              </button>
            )}
          </div>
          <textarea
            className="field mt-2 min-h-[130px] resize-y"
            placeholder={supported ? 'Speak or type your answer…' : 'Type your answer…'}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
          <div className="mt-3 flex items-center gap-3">
            <button className="btn-dark" disabled={!answer.trim() || busy} onClick={submit}>
              {busy ? 'Submitting…'
                : stage === 'followup'
                  ? (index + 1 < total ? 'Submit & next item' : 'Submit & finish')
                  : 'Submit answer'}
            </button>
            {err && <span className="text-sm text-[#C8352B]">{err}</span>}
          </div>
          <p className="mt-3 text-xs text-muted">No feedback is shown during the interview — your result goes to the company at the end.</p>
        </div>
      </div>
    </main>
  );
}
