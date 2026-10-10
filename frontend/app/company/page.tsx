'use client';
import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AppBar from '@/components/AppBar';
import { getToken, getRole, companyItems, verifyCompanyItem, createCompanyItem, deleteCompanyItem, generateCompanyItem } from '@/lib/api';

type BankItem = {
  item_id: string; domain: string; level: string; language: string;
  prompt: string; fault_id: string; authored: boolean; created_at: string | null;
};
const DOMAIN_LABEL: Record<string, string> = { core_se: 'Core SE', database: 'Database' };

// a known-good example (off-by-one that crashes) to get authors started
const EXAMPLE = {
  domain: 'core_se', level: 'engineer', language: 'python',
  prompt: 'Read this function. Explain what it returns and whether it is correct for all inputs.',
  code: 'def last(a):\n    return a[len(a)]\n',
  fault_id: 'CORR-INDEX', fault_description: 'Indexing at len(a) is one past the end; it should be len(a)-1.',
  observations: ['Means to return the last element of a.', 'a[len(a)] is out of range → IndexError.', 'Fix: return a[len(a)-1] or a[-1].'],
  decoy_looks_wrong: '', decoy_actually_fine: '',
  reference: 'def last(a):\n    return a[len(a)-1]\n',
  probe: 'result = last([1, 2, 3])',
  setup: '', entry: '', min_ratio: 20,
  schema: '', correct: '',
};

type Verdict = { passed: boolean; summary: string } | null;

export default function CompanyPage() {
  const router = useRouter();
  const [bank, setBank] = useState<BankItem[]>([]);
  const [f, setF] = useState({ ...EXAMPLE });
  const [kind, setKind] = useState<'python_diff' | 'python_perf' | 'sql_diff'>('python_diff');
  const [verdict, setVerdict] = useState<Verdict>(null);
  const [busy, setBusy] = useState(false);
  const [published, setPublished] = useState('');
  const [err, setErr] = useState('');
  // generate-from-document panel
  const [position, setPosition] = useState('');
  const [docText, setDocText] = useState('');
  const [docFile, setDocFile] = useState<File | null>(null);
  const [genBusy, setGenBusy] = useState(false);
  const [genMsg, setGenMsg] = useState('');
  const [genErr, setGenErr] = useState('');

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    if (getRole() !== 'company') { router.push('/recruiter'); return; }
  }, [router]);

  const load = useCallback(() => { companyItems().then(setBank).catch(() => {}); }, []);
  useEffect(() => { if (getToken()) load(); }, [load]);

  // keep check kind valid for the chosen language
  useEffect(() => {
    if (f.language === 'sql' && kind !== 'sql_diff') setKind('sql_diff');
    if (f.language === 'python' && kind === 'sql_diff') setKind('python_diff');
  }, [f.language, kind]);

  function buildCheck(): Record<string, unknown> {
    if (kind === 'python_diff') return { kind, reference: f.reference, probe: f.probe };
    if (kind === 'python_perf') return { kind, reference: f.reference, setup: f.setup, entry: f.entry, min_ratio: Number(f.min_ratio) || 20 };
    return { kind, schema: f.schema, correct: f.correct };
  }
  function draft(): Record<string, unknown> {
    return {
      domain: f.domain, level: f.level, language: f.language, prompt: f.prompt, code: f.code,
      fault_id: f.fault_id, fault_description: f.fault_description,
      observations: f.observations.filter((o) => o.trim()),
      decoy_looks_wrong: f.decoy_looks_wrong, decoy_actually_fine: f.decoy_actually_fine,
      check: buildCheck(),
    };
  }

  async function runVerify() {
    setBusy(true); setErr(''); setVerdict(null); setPublished('');
    try { setVerdict(await verifyCompanyItem(draft())); }
    catch (e: any) { setErr(e.message || 'Verify failed'); }
    finally { setBusy(false); }
  }
  async function publish() {
    setBusy(true); setErr('');
    try {
      const r = await createCompanyItem(draft());
      setPublished(r.item_id); setVerdict(null); load();
    } catch (e: any) { setErr(e.message || 'Publish failed'); }
    finally { setBusy(false); }
  }
  async function remove(id: string) {
    try { await deleteCompanyItem(id); load(); } catch (e: any) { setErr(e.message); }
  }

  // drop a generated/returned draft into the authoring form, ready to review + publish
  function applyDraft(d: any) {
    const chk = d.check || {};
    setKind(chk.kind || 'python_diff');
    setF((s) => ({
      ...s,
      domain: d.domain ?? s.domain, level: d.level ?? s.level, language: d.language ?? s.language,
      prompt: d.prompt ?? s.prompt, code: d.code ?? '',
      fault_id: d.fault_id ?? '', fault_description: d.fault_description ?? '',
      observations: (d.observations && d.observations.length ? d.observations : ['', '', '']),
      decoy_looks_wrong: d.decoy_looks_wrong ?? '', decoy_actually_fine: d.decoy_actually_fine ?? '',
      reference: chk.reference ?? '', probe: chk.probe ?? '',
      setup: chk.setup ?? '', entry: chk.entry ?? '', min_ratio: chk.min_ratio ?? 20,
      schema: chk.schema ?? '', correct: chk.correct ?? '',
    }));
  }

  async function generate() {
    setGenBusy(true); setGenErr(''); setGenMsg(''); setVerdict(null); setPublished('');
    try {
      const form = new FormData();
      form.set('domain', f.domain); form.set('level', f.level); form.set('language', f.language);
      form.set('position', position); form.set('source_text', docText);
      if (docFile) form.set('file', docFile);
      const r = await generateCompanyItem(form);
      applyDraft(r.draft);
      setVerdict({ passed: !!r.verified, summary: r.oracle });  // already oracle-verified → ready to publish
      setGenMsg(r.source === 'ai'
        ? 'Drafted from your document by AI and verified by the oracle — review below and publish.'
        : 'AI generation was unavailable, so this is a verified template matched to the role — review below and publish.');
    } catch (e: any) { setGenErr(e.message || 'Generation failed'); }
    finally { setGenBusy(false); }
  }

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setF((s) => ({ ...s, [k]: e.target.value }));
  const setObs = (i: number, v: string) =>
    setF((s) => ({ ...s, observations: s.observations.map((o, j) => (j === i ? v : o)) }));

  return (
    <main className="min-h-screen">
      <AppBar />
      <div className="wrap py-8">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted">Company · test authoring</p>
            <h1 className="font-serif text-4xl leading-tight">Your test bank</h1>
          </div>
          <button onClick={() => router.push('/recruiter')} className="btn-ghost">Candidate pool →</button>
        </div>
        <p className="mt-2 max-w-2xl text-muted">
          Create your own comprehension items. Every test must pass the verification oracle — it runs your
          buggy code against your reference fix and only publishes if the fault actually bites. No broken tests go live.
        </p>

        {/* generate from a document */}
        <section className="mt-6 rounded-2xl border border-line bg-white p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="font-serif text-xl">Generate from a document</h2>
              <p className="mt-0.5 max-w-2xl text-sm text-muted">
                Upload a job description or topic sheet (or paste it below) and the role you&apos;re hiring for.
                We draft AI-style code with one real fault at that level, prove it bites, and fill the form below for you to review.
              </p>
            </div>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-[1.4fr_1fr_1fr]">
            <Field label="Position you're hiring for">
              <input className="field" value={position} onChange={(e) => setPosition(e.target.value)}
                     placeholder="e.g. Senior Backend Engineer at Devsinc" /></Field>
            <Field label="Domain"><select className="field" value={f.domain} onChange={set('domain')}>
              <option value="core_se">Core SE</option><option value="database">Database</option></select></Field>
            <Field label="Level"><select className="field" value={f.level} onChange={set('level')}>
              <option value="associate">Associate</option><option value="engineer">Engineer</option><option value="senior">Senior</option></select></Field>
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <Field label="Upload a document (.txt, .md, .pdf, .docx)">
              <input type="file" accept=".txt,.md,.markdown,.pdf,.docx,.csv,.rtf"
                     onChange={(e) => setDocFile(e.target.files?.[0] ?? null)}
                     className="block w-full text-sm text-muted file:mr-3 file:rounded-pill file:border file:border-line file:bg-sand file:px-3 file:py-1.5 file:text-ink" />
              {docFile && <span className="mt-1 block text-xs text-muted">{docFile.name}</span>}
            </Field>
            <Field label="…or paste the content">
              <textarea className="field min-h-[72px]" value={docText} onChange={(e) => setDocText(e.target.value)}
                        placeholder="Paste a JD, a list of topics the role must cover, or interview notes." /></Field>
          </div>

          {genMsg && <p className="mt-3 rounded-xl border border-[#BBD4FB] bg-[#EAF1FE] p-3 text-sm text-[#0A66F0]">{genMsg}</p>}
          {genErr && <p className="mt-3 text-sm text-brand">{genErr}</p>}

          <div className="mt-4">
            <button className="btn-dark" onClick={generate} disabled={genBusy}>
              {genBusy ? 'Generating…' : 'Generate test'}</button>
          </div>
        </section>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_360px]">
          {/* authoring form */}
          <section className="panel p-6">
            <div className="flex items-center justify-between">
              <h2 className="font-serif text-xl">New test</h2>
              <button onClick={() => { setF({ ...EXAMPLE }); setKind('python_diff'); setVerdict(null); setPublished(''); }}
                      className="text-sm text-muted hover:text-ink">Fill example</button>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2">
              <Field label="Domain"><select className="field" value={f.domain} onChange={set('domain')}>
                <option value="core_se">Core SE</option><option value="database">Database</option></select></Field>
              <Field label="Level"><select className="field" value={f.level} onChange={set('level')}>
                <option value="associate">Associate</option><option value="engineer">Engineer</option><option value="senior">Senior</option></select></Field>
              <Field label="Language"><select className="field" value={f.language} onChange={set('language')}>
                <option value="python">Python</option><option value="sql">SQL</option></select></Field>
            </div>

            <Field label="Prompt" className="mt-3">
              <textarea className="field min-h-[56px]" value={f.prompt} onChange={set('prompt')} /></Field>
            <Field label="Code the candidate reads (contains the fault)" className="mt-3">
              <textarea className="field min-h-[110px] font-mono text-sm" value={f.code} onChange={set('code')} /></Field>

            <div className="mt-3 grid grid-cols-[160px_1fr] gap-2">
              <Field label="Fault id"><input className="field" value={f.fault_id} onChange={set('fault_id')} /></Field>
              <Field label="What the fault is"><input className="field" value={f.fault_description} onChange={set('fault_description')} /></Field>
            </div>

            <Field label="What a strong answer covers (first 3 are required)" className="mt-3">
              <div className="space-y-2">
                {f.observations.map((o, i) => (
                  <input key={i} className="field" value={o} placeholder={`Observation ${i + 1}`}
                         onChange={(e) => setObs(i, e.target.value)} />
                ))}
                <button onClick={() => setF((s) => ({ ...s, observations: [...s.observations, ''] }))}
                        className="text-sm text-muted hover:text-ink">+ add observation</button>
              </div>
            </Field>

            {/* the executable check */}
            <div className="mt-5 rounded-xl border border-line bg-white p-4">
              <p className="text-sm font-semibold text-ink">Verification check</p>
              <p className="text-xs text-muted">How the oracle proves the fault bites.</p>
              <div className="mt-3">
                <Field label="Check type">
                  <select className="field" value={kind} onChange={(e) => setKind(e.target.value as any)}>
                    {f.language === 'python' && <option value="python_diff">Python · wrong output / crash</option>}
                    {f.language === 'python' && <option value="python_perf">Python · too slow (complexity)</option>}
                    {f.language === 'sql' && <option value="sql_diff">SQL · wrong result set</option>}
                  </select>
                </Field>
                {kind === 'python_diff' && (<>
                  <Field label="Reference (the fixed code)" className="mt-2">
                    <textarea className="field min-h-[80px] font-mono text-sm" value={f.reference} onChange={set('reference')} /></Field>
                  <Field label="Probe (set `result` using the function)" className="mt-2">
                    <textarea className="field min-h-[48px] font-mono text-sm" value={f.probe} onChange={set('probe')} /></Field>
                </>)}
                {kind === 'python_perf' && (<>
                  <Field label="Reference (the fast fix)" className="mt-2">
                    <textarea className="field min-h-[80px] font-mono text-sm" value={f.reference} onChange={set('reference')} /></Field>
                  <div className="mt-2 grid grid-cols-[1fr_120px] gap-2">
                    <Field label="Entry function"><input className="field font-mono text-sm" value={f.entry} onChange={set('entry')} /></Field>
                    <Field label="Min ratio ×"><input className="field" value={f.min_ratio} onChange={set('min_ratio')} /></Field>
                  </div>
                  <Field label="Setup (build `args` tuple, e.g. args = (list(range(20000)),) )" className="mt-2">
                    <textarea className="field min-h-[48px] font-mono text-sm" value={f.setup} onChange={set('setup')} /></Field>
                </>)}
                {kind === 'sql_diff' && (<>
                  <Field label="Schema + seed (CREATE … ; INSERT … ;)" className="mt-2">
                    <textarea className="field min-h-[90px] font-mono text-sm" value={f.schema} onChange={set('schema')} /></Field>
                  <Field label="Correct query (the fix)" className="mt-2">
                    <textarea className="field min-h-[60px] font-mono text-sm" value={f.correct} onChange={set('correct')} /></Field>
                </>)}
              </div>
            </div>

            {/* verdict + actions */}
            {verdict && (
              <div className={`mt-4 rounded-xl border p-3 text-sm ${verdict.passed
                ? 'border-[#BBD4FB] bg-[#EAF1FE] text-[#0A66F0]' : 'border-[#EFC9C3] bg-[#FBECEA] text-[#C8352B]'}`}>
                <span className="font-semibold">{verdict.passed ? '✓ Fault bites — ready to publish' : '✗ Fault does not bite'}</span>
                <p className="mt-0.5 text-muted">{verdict.summary}</p>
              </div>
            )}
            {published && <p className="mt-4 rounded-xl border border-[#BBD4FB] bg-[#EAF1FE] p-3 text-sm text-[#0A66F0]">Published <span className="font-mono">{published}</span> — it&apos;s now live for candidates.</p>}
            {err && <p className="mt-3 text-sm text-brand">{err}</p>}

            <div className="mt-4 flex gap-3">
              <button className="btn-ghost" onClick={runVerify} disabled={busy}>{busy ? 'Running…' : 'Verify with oracle'}</button>
              <button className="btn-dark" onClick={publish} disabled={busy || !verdict?.passed}>Publish test</button>
            </div>
          </section>

          {/* bank */}
          <aside>
            <p className="text-sm text-muted">Published items ({bank.length})</p>
            <ul className="mt-3 space-y-2">
              {bank.map((it) => (
                <li key={it.item_id} className="lift rounded-2xl border border-line bg-white p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-mono text-xs text-muted">{it.item_id}</p>
                      <p className="mt-0.5 text-sm text-ink">{DOMAIN_LABEL[it.domain] ?? it.domain} · {it.level} · {it.language}</p>
                      <p className="mt-1 text-xs text-muted">{it.fault_id}{it.authored ? '' : ' · seed'}</p>
                    </div>
                    {it.authored && (
                      <button onClick={() => remove(it.item_id)} className="text-xs text-muted hover:text-[#C8352B]">delete</button>
                    )}
                  </div>
                </li>
              ))}
              {bank.length === 0 && <li className="text-sm text-muted">No items yet.</li>}
            </ul>
          </aside>
        </div>
      </div>
    </main>
  );
}

function Field({ label, children, className = '' }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 block text-xs font-medium text-ink">{label}</span>
      {children}
    </label>
  );
}
