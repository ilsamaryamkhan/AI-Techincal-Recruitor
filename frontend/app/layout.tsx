import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'asaanHire — where talent becomes teams',
  description: 'asaanHire measures whether people can read, debug and explain AI-written code — proctored, scored, and turned into a credential.',
  icons: { icon: '/favicon.png' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
