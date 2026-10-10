import Logo from './Logo';

export default function Footer() {
  return (
    <footer className="mt-24 border-t border-line">
      <div className="wrap flex flex-col gap-6 py-10 md:flex-row md:items-center md:justify-between">
        <Logo />
        <p className="max-w-sm text-sm text-muted">
          The skill that survived AI isn&apos;t writing code — it&apos;s knowing when the code is wrong.
          asaanHire measures it.
        </p>
        <p className="text-sm text-muted">© {new Date().getFullYear()} asaanHire</p>
      </div>
    </footer>
  );
}
