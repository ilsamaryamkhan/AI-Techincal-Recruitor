'use client';
import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AppBar from '@/components/AppBar';
import CredentialBadge from '@/components/CredentialBadge';
import VerifyScore from '@/components/VerifyScore';
import { getToken, getRole, listCompanies, recruiterStats, recruiterCandidates } from '@/lib/api';

type Candidate = {
  user_id: number; name: string; email: string;
  verify_score: number; verify_best: number; calibration: number;
  fluent_wrongness_total: number; items_attempted: number;
  credential: 'verified' | 'developing' | 'unverified';
  verified: boolean; top_domain: string | null; domains: string[];
  last_active: string | null;
};
type Stats = { candidates: number; verified: number; fluent_wrongness_flagged: number; avg_verify: number };

const DOMAIN_LABEL: Record<string, string> = {
  core_se: 'Core SE', database: 'Database', web: 'Web', qa: 'QA', ml: 'AI/ML',
};
const DOMAINS = ['core_se', 'database', 'web', 'qa', 'ml'];
const LEVELS = ['associate', 'engineer', 'senior'];
const SORTS = [
  ['verify', 'Verify score'],
  ['calibration', 'Calibration'],
  ['fluent', 'Most confidently-wrong'],
  ['recent', 'Recently active'],
];

function ago(iso: string | null) {
  if (!iso) return '—';
  const d = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  return d <= 0 ? 'today' : d === 1 ? 'yesterday' : `${d}d ago`;
}

export default function RecruiterPage() {
  const router = useRouter();
  const [rows, setRows] = useState<Candidate[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [companies, setCompanies] = useState<{ id: string; name: string }[]>([]);
  const [f, setF] = useState({ domain: '', company_id: '', level: '', credential: '', min_verify: '0', sort: 'verify' });
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    const role = getRole();
    if (role !== 'recruiter' && role !== 'company') { router.push('/practice'); return; }
    recruiterStats().then(setStats).catch(() => {});
    listCompanies().then(setCompanies).catch(() => {});
  }, [router]);

  const load = useCallback(async () => {
    setLoading(true); setErr('');
    const q = new URLSearchParams();
    if (f.domain) q.set('domain', f.domain);
    if (f.company_id) q.set('company_id', f.company_id);
    if (f.level) q.set('level', f.level);
    if (f.credential) q.set('credential', f.credential);
    if (f.min_verify !== '0') q.set('min_verify', f.min_verify);
    q.set('sort', f.sort);
    try {
      setRows(await recruiterCandidates(`?${q.toString()}`));
    } catch (e: any) { setErr(e.message || 'Could not load candidates'); }
    finally { setLoading(false); }
  }, [f]);

  useEffect(() => { if (getToken()) load(); }, [load]);

  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLSelectElement>) =>
    setF((s) => ({ ...s, [k]: e.target.value }));

  return (
    <main className="min-h-screen">
      <AppBar />
      <div className="wrap py-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm text-muted">Recruiter</p>
            <h1 className="font-serif text-4xl leading-tight">Candidate pool</h1>
            <p className="mt-1 max-w-xl text-muted">
              Every candidate, scored on whether they can tell when AI-written code is wrong — not just whether they sound right.
            </p>
          </div>
          {getRole() === 'company' && (
            <button onClick={() => router.push('/company')} className="btn-ghost shrink-0">Author tests</button>
          )}
        </div>

        {/* stat tiles */}
        {stats && (
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Tile label="Candidates" value={stats.candidates} />
            <Tile label="Verified" value={stats.verified} />
            <Tile label="Avg verify" value={stats.avg_verify} />
            <Tile label="Confidently-wrong flagged" value={stats.fluent_wrongness_flagged}
                  tone={stats.fluent_wrongness_flagged > 0 ? 'warn' : undefined} />
          </div>
        )}

        {/* filters */}
        <div className="mt-6 flex flex-wrap items-center gap-2">
          <Select value={f.sort} onChange={set('sort')} label="Sort">
            {SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
          <Select value={f.domain} onChange={set('domain')} label="Domain">
            <option value="">All domains</option>
            {DOMAINS.map((d) => <option key={d} value={d}>{DOMAIN_LABEL[d]}</option>)}
          </Select>
          <Select value={f.company_id} onChange={set('company_id')} label="Company">
            <option value="">All companies</option>
            {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
          <Select value={f.level} onChange={set('level')} label="Level">
            <option value="">Any level</option>
            {LEVELS.map((l) => <option key={l} value={l}>{l[0].toUpperCase() + l.slice(1)}</option>)}
          </Select>
          <Select value={f.credential} onChange={set('credential')} label="Credential">
            <option value="">Any credential</option>
            <option value="verified">Verified</option>
            <option value="developing">Developing</option>
            <option value="unverified">Unverified</option>
          </Select>
          <Select value={f.min_verify} onChange={set('min_verify')} label="Min verify">
            {['0', '50', '70', '80', '90'].map((v) => <option key={v} value={v}>{v === '0' ? 'Any score' : `${v}+`}</option>)}
          </Select>
        </div>

        {/* table header (md+) */}
        <div className="mt-6 hidden grid-cols-[1.6fr_0.7fr_1fr_0.9fr_1.1fr_0.8fr_0.7fr] gap-3 px-4 text-xs uppercase tracking-wide text-muted md:grid">
          <span>Candidate</span><span>Verify</span><span>Credential</span>
          <span>Calibration</span><span>Confidently wrong</span><span>Domain</span><span className="text-right">Active</span>
        </div>

        {err && <p className="mt-4 text-sm text-brand">{err}</p>}
        {loading ? (
          <p className="mt-6 text-muted">Loading candidates…</p>
        ) : rows.length === 0 ? (
          <p className="mt-6 text-muted">No candidates match these filters.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {rows.map((c) => (
              <li key={c.user_id}>
                <button
                  onClick={() => router.push(`/recruiter/${c.user_id}`)}
                  className="lift w-full rounded-2xl border border-line bg-white px-4 py-4 text-left hover:bg-sand
                             md:grid md:grid-cols-[1.6fr_0.7fr_1fr_0.9fr_1.1fr_0.8fr_0.7fr] md:items-center md:gap-3"
                >
                  <div>
                    <p className="font-medium text-ink">{c.name}</p>
                    <p className="text-xs text-muted">{c.items_attempted} item{c.items_attempted === 1 ? '' : 's'} · {c.email}</p>
                  </div>
                  <div className="mt-3 flex items-center gap-2 md:mt-0">
                    <VerifyScore score={c.verify_score} />
                    <span className="text-xs text-muted md:hidden">verify</span>
                  </div>
                  <div className="mt-3 md:mt-0"><CredentialBadge level={c.credential} /></div>
                  <div className="mt-2 text-sm text-ink md:mt-0">
                    {c.calibration}<span className="text-muted md:hidden"> calibration</span>
                  </div>
                  <div className="mt-2 md:mt-0">
                    {c.fluent_wrongness_total > 0 ? (
                      <span className="inline-flex items-center rounded-pill bg-[#FBECEA] px-2.5 py-0.5 text-xs font-medium text-[#C8352B]">
                        {c.fluent_wrongness_total} flagged
                      </span>
                    ) : (
                      <span className="text-sm text-muted">clean</span>
                    )}
                  </div>
                  <div className="mt-2 text-sm text-muted md:mt-0">
                    {c.top_domain ? DOMAIN_LABEL[c.top_domain] ?? c.top_domain : '—'}
                  </div>
                  <div className="mt-2 text-sm text-muted md:mt-0 md:text-right">{ago(c.last_active)}</div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}

function Tile({ label, value, tone }: { label: string; value: number; tone?: 'warn' }) {
  return (
    <div className="lift panel p-4">
      <p className={`font-serif text-3xl leading-none ${tone === 'warn' ? 'text-[#C8352B]' : 'text-ink'}`}>{value}</p>
      <p className="mt-1 text-xs text-muted">{label}</p>
    </div>
  );
}

function Select({ value, onChange, label, children }:
  { value: string; onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void; label: string; children: React.ReactNode }) {
  return (
    <label className="inline-flex items-center gap-2 rounded-pill border border-line bg-white px-3 py-1.5 text-sm">
      <span className="text-xs text-muted">{label}</span>
      <select value={value} onChange={onChange} className="bg-transparent text-ink outline-none">
        {children}
      </select>
    </label>
  );
}
