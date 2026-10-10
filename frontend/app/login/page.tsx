'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Logo from '@/components/Logo';
import { login, saveAuth } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(''); setBusy(true);
    try {
      const { access_token, role } = await login(email, password);
      saveAuth(access_token, role);
      router.push(role === 'candidate' ? '/practice' : '/recruiter');
    } catch (e: any) {
      setErr(e.message || 'Could not log in');
    } finally { setBusy(false); }
  }

  return (
    <main className="min-h-screen">
      <div className="wrap flex h-16 items-center justify-between">
        <Logo />
        <Link href="/signup" className="btn-ghost">Sign up</Link>
      </div>
      <div className="wrap mx-auto flex max-w-md flex-col justify-center pt-24">
        <h1 className="font-serif text-4xl">Log in</h1>
        <p className="mt-1 text-muted">Welcome back.</p>
        <form onSubmit={submit} className="mt-8 space-y-3">
          <input className="field" type="email" placeholder="Email" value={email}
                 onChange={(e) => setEmail(e.target.value)} required />
          <input className="field" type="password" placeholder="Password" value={password}
                 onChange={(e) => setPassword(e.target.value)} required />
          {err && <p className="text-sm text-brand">{err}</p>}
          <button className="btn-dark w-full py-3 text-base" disabled={busy}>
            {busy ? 'Logging in…' : 'Log in'}
          </button>
        </form>
        <p className="mt-5 text-sm text-muted">
          New here? <Link href="/signup" className="text-ink underline">Create an account</Link>
        </p>
      </div>
    </main>
  );
}
