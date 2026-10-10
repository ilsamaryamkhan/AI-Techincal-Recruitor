'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AppBar from '@/components/AppBar';
import CodePanel from '@/components/CodePanel';
import ResultPanel, { PracticeResult } from '@/components/ResultPanel';
import { getToken, listItems, submitPractice } from '@/lib/api';

type Item = {
  item_id: string; company_id: string; domain: string; level: string;
  mode: string; language: string; prompt: string;
  artifact: { files: { path: string; content: string }[] };
};

const DOMAIN_LABEL: Record<string, string> = {
  core_se: 'Core SE', database: 'Database', web: 'Web', qa: 'QA', ml: 'AI/ML',
};

export default function PracticePage() {
  const router = useRouter();
  const [items, setItems] = useState<Item[]>([]);
  const [active, setActive] = useState<Item | null>(null);
  const [explanation, setExplanation] = useState('');
  const [result, setResult] = useState<PracticeResult | null>(null);
  const [grading, setGrading] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    listItems()
      .then((data: Item[]) => { setItems(data); setActive(data[0] ?? null); })
      .catch((e) => setErr(e.message));
  }, [router]);

  function pick(it: Item) { setActive(it); setExplanation(''); setResult(null); setErr(''); }

  async function submit() {
    if (!active || !explanation.trim()) return;
    setGrading(true); setErr('');
    try {
      const r = await submitPractice(active.item_id, explanation);
      setResult(r);
    } catch (e: any) {
      setErr(e.message || 'Grading failed');
    } finally { setGrading(false); }
  }

  return (
    <main className="min-h-screen">
      <AppBar />
      <div className="wrap grid gap-6 py-8 md:grid-cols-[260px_1fr]">
        {/* item list */}
        <aside>
          <button
            onClick={() => router.push('/interview')}
            className="mb-5 flex w-full items-center justify-between rounded-2xl border border-ink bg-ink px-4 py-3 text-left text-paper transition-colors hover:bg-black"
          >
            <span>
              <span className="block text-sm font-medium">Live interview</span>
              <span className="block text-xs text-paper/70">Proctored · scored · timed</span>
            </span>
            <span aria-hidden>→</span>
          </button>
          <p className="text-sm text-muted">Practice items</p>
          {err && <p className="mt-3 text-sm text-brand">{err}</p>}
          <ul className="mt-3 space-y-1.5">
            {items.map((it) => (
              <li key={it.item_id}>
                <button
                  onClick={() => pick(it)}
                  className={`lift w-full rounded-xl border px-3 py-2.5 text-left ${
                    active?.item_id === it.item_id
                      ? 'border-ink/30 bg-sand' : 'border-line bg-white hover:bg-sand'
                  }`}
                >
                  <span className="block text-sm font-medium text-ink">{DOMAIN_LABEL[it.domain] ?? it.domain}</span>
                  <span className="block text-xs text-muted">{it.company_id} · {it.level}</span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {/* workspace */}
        <section>
          {active ? (
            <>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
                <span className="rounded-pill bg-sand px-2.5 py-0.5">{active.company_id}</span>
                <span className="rounded-pill bg-sand px-2.5 py-0.5">{DOMAIN_LABEL[active.domain] ?? active.domain}</span>
                <span className="rounded-pill bg-sand px-2.5 py-0.5">{active.level}</span>
                <span className="rounded-pill bg-sand px-2.5 py-0.5">{active.mode}</span>
              </div>
              <h1 className="mt-4 font-serif text-2xl leading-snug">{active.prompt}</h1>

              <div className="mt-5">
                <CodePanel code={active.artifact.files[0]?.content ?? ''} language={active.language} />
              </div>

              {result ? (
                <div className="mt-6">
                  <ResultPanel r={result} onRetry={() => { setResult(null); setExplanation(''); }} />
                </div>
              ) : (
                <div className="mt-6">
                  <label className="text-sm font-medium text-ink">Your explanation</label>
                  <p className="text-sm text-muted">Explain what the code does, its complexity, and anything you&apos;d flag in review.</p>
                  <textarea
                    className="field mt-3 min-h-[140px] resize-y"
                    placeholder="Type your explanation…"
                    value={explanation}
                    onChange={(e) => setExplanation(e.target.value)}
                  />
                  <div className="mt-3 flex items-center gap-3">
                    <button className="btn-dark" disabled={!explanation.trim() || grading} onClick={submit}>
                      {grading ? 'Grading…' : 'Submit explanation'}
                    </button>
                    {err && <span className="text-sm text-[#C8352B]">{err}</span>}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-muted">{err ? '' : 'Loading practice items…'}</p>
          )}
        </section>
      </div>
    </main>
  );
}
