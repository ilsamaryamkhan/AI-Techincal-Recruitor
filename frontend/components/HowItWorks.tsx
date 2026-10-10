'use client';
import { useState } from 'react';

const STEPS = {
  candidate: [
    { t: 'Practice against a company’s real bar', d: 'Pick a company and domain. Work through fresh items modelled on how they actually hire — explain, debug, optimise. Clear their threshold to unlock the live round.' },
    { t: 'Sit the comprehension interview', d: 'An AI shows you real code and asks you to explain it — what it does, where it breaks, what it costs. You write no code. Camera on, scored live.' },
    { t: 'Own a verified credential', d: 'Your comprehension score and trust-calibration become a profile you control. Make it public to share one signed link with any recruiter.' },
  ],
  company: [
    { t: 'Upload how you already hire', d: 'Drop in your sample tests, reference solutions and rubrics. asaanHire learns your bar — it never reuses your exact questions.' },
    { t: 'Send one standardised round', d: 'Candidates sit a proctored code-comprehension interview. Every answer is graded against executable ground truth, not vibes.' },
    { t: 'Read a ranked, trustworthy pool', d: 'See who can actually read code, each with an integrity-confidence score. Stop first-rounding people who only prompt well.' },
  ],
};

export default function HowItWorks() {
  const [who, setWho] = useState<'candidate' | 'company'>('candidate');
  const steps = STEPS[who];
  return (
    <section id="how" className="wrap scroll-mt-20 py-20">
      <h2 className="mx-auto max-w-2xl text-center font-serif text-4xl leading-tight md:text-5xl">
        For everyone making their next move
      </h2>
      <div className="mt-8 flex justify-center">
        <div className="inline-flex rounded-pill border border-line bg-sand p-1">
          {(['candidate', 'company'] as const).map((k) => (
            <button
              key={k}
              onClick={() => setWho(k)}
              className={`rounded-pill px-5 py-2 text-sm font-medium transition-colors ${
                who === k ? 'bg-white text-ink shadow-sm' : 'text-muted hover:text-ink'
              }`}
            >
              {k === 'candidate' ? 'Candidates' : 'Companies'}
            </button>
          ))}
        </div>
      </div>

      <ol className="mx-auto mt-12 grid max-w-4xl gap-5 md:grid-cols-3">
        {steps.map((s, i) => (
          <li key={i} className="lift panel flex flex-col gap-3 p-6">
            <span className="font-serif text-2xl text-brand">{i + 1}</span>
            <h3 className="text-lg font-semibold leading-snug">{s.t}</h3>
            <p className="text-sm leading-relaxed text-muted">{s.d}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
