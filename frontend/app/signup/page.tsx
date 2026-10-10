'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Logo from '@/components/Logo';
import { register, saveAuth, listCompanies } from '@/lib/api';

type Role = 'candidate' | 'company';

export default function SignupPage() {
  const router = useRouter();
  const [role, setRole] = useState<Role | null>(null);
  const [companies, setCompanies] = useState<{ id: string; name: string }[]>([]);
  const [form, setForm] = useState({ full_name: '', email: '', password: '', company_id: '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => { listCompanies().then(setCompanies).catch(() => {}); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(''); setBusy(true);
    try {
      const body: any = { ...form, role };
      if (role !== 'company') delete body.company_id;
      const { access_token, role: r } = await register(body);
      saveAuth(access_token, r);
      router.push(r === 'candidate' ? '/practice' : '/recruiter');
    } catch (e: any) {
      setErr(e.message || 'Could not sign up');
    } finally { setBusy(false); }
  }

  return (
    <main className="min-h-screen">
      <div className="wrap flex h-16 items-center justify-between">
        <Logo />
        <Link href="/login" className="btn-ghost">Log in</Link>
      </div>

      <div className="wrap mx-auto flex max-w-md flex-col justify-center pt-24">
        <h1 className="font-serif text-4xl">Sign up</h1>
        <p className="mt-1 text-muted">Create your asaanHire account.</p>

        {!role ? (
          <div className="mt-8 space-y-3">
            <button onClick={() => setRole('candidate')}
                    className="lift panel flex w-full items-center justify-between bg-white p-4 text-left hover:bg-sand">
              <span><span className="block font-medium text-ink">I&apos;m looking for a role</span>
                <span className="text-sm text-muted">Practise and earn a verified credential</span></span>
              <span className="text-muted">→</span>
            </button>
            <button onClick={() => setRole('company')}
                    className="lift panel flex w-full items-center justify-between bg-white p-4 text-left hover:bg-sand">
              <span><span className="block font-medium text-ink">I&apos;m hiring</span>
                <span className="text-sm text-muted">Screen candidates on code comprehension</span></span>
              <span className="text-muted">→</span>
            </button>
          </div>
        ) : (
          <form onSubmit={submit} className="mt-8 space-y-3">
            <button type="button" onClick={() => setRole(null)} className="text-sm text-muted hover:text-ink">← back</button>
            <input className="field" placeholder="Full name" value={form.full_name}
                   onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
            <input className="field" type="email" placeholder="Email" value={form.email}
                   onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            <input className="field" type="password" placeholder="Password (min 6 chars)" value={form.password}
                   onChange={(e) => setForm({ ...form, password: e.target.value })} minLength={6} required />
            {role === 'company' && (
              <select className="field" value={form.company_id}
                      onChange={(e) => setForm({ ...form, company_id: e.target.value })} required>
                <option value="">Select your company</option>
                {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            )}
            {err && <p className="text-sm text-brand">{err}</p>}
            <button className="btn-dark w-full py-3 text-base" disabled={busy}>
              {busy ? 'Creating…' : 'Create account'}
            </button>
          </form>
        )}

        <p className="mt-5 text-sm text-muted">
          Already have an account? <Link href="/login" className="text-ink underline">Log in</Link>
        </p>
      </div>
    </main>
  );
}
