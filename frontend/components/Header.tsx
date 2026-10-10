import Link from 'next/link';
import Logo from './Logo';

const nav = [
  { label: 'For candidates', href: '/#candidates' },
  { label: 'For companies', href: '/#companies' },
  { label: 'How it works', href: '/#how' },
];

export default function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-line/60 bg-paper/85 backdrop-blur">
      <div className="wrap flex h-16 items-center justify-between">
        <Logo />
        <nav className="hidden items-center gap-8 md:flex">
          {nav.map((n) => (
            <Link key={n.href} href={n.href} className="navlink text-sm text-muted hover:text-ink">
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link href="/login" className="btn-ghost">Log in</Link>
          <Link href="/signup" className="btn-dark">Sign up</Link>
        </div>
      </div>
    </header>
  );
}
