import Link from 'next/link';

export default function Logo({ className = '' }: { className?: string }) {
  return (
    <Link href="/" className={`inline-flex items-center gap-2 ${className}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/logo.png" alt="" className="h-7 w-auto" />
      <span className="font-serif text-xl leading-none tracking-tight text-ink">
        asaan<span className="text-brand">Hire</span>
      </span>
    </Link>
  );
}
