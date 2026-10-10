'use client';
import { useRouter } from 'next/navigation';
import Logo from './Logo';
import { clearAuth } from '@/lib/api';

export default function AppBar() {
  const router = useRouter();
  return (
    <header className="border-b border-line bg-paper/85 backdrop-blur">
      <div className="wrap flex h-16 items-center justify-between">
        <Logo />
        <button onClick={() => { clearAuth(); router.push('/'); }}
                className="text-sm text-muted transition-colors hover:text-ink">
          Log out
        </button>
      </div>
    </header>
  );
}
