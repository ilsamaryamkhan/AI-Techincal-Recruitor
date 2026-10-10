import Link from 'next/link';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import AnimatedHeadline from '@/components/AnimatedHeadline';
import HowItWorks from '@/components/HowItWorks';

const COMPANIES = ['Devsinc', 'Systems Limited', 'Techlogix', '10Pearls', 'Arbisoft',
  'NETSOL', 'Folio3', 'Confiz', 'VentureDive', 'i2c'];

export default function Home() {
  return (
    <>
      <Header />

      {/* ---- hero ---- */}
      <section className="wrap pt-20 pb-16 text-center md:pt-28">
        <AnimatedHeadline
          text="Where talented individuals|become extraordinary teams."
          className="mx-auto max-w-4xl font-serif text-4xl font-medium leading-[1.1] tracking-tight md:text-6xl"
        />
        <p className="mx-auto mt-7 max-w-xl text-lg leading-relaxed text-muted">
          Anyone can prompt an AI to write code. asaanHire measures the rarer skill —
          reading it, catching what&apos;s wrong, and proving you can.
        </p>
        <div className="mt-9 flex flex-wrap justify-center gap-3">
          <Link href="/signup" className="btn-dark px-6 py-3 text-base">Start practising</Link>
          <Link href="/#companies" className="btn-ghost px-6 py-3 text-base">Hire with asaanHire</Link>
        </div>
      </section>

      {/* ---- two-column split (equal height, top-aligned) ---- */}
      <section className="wrap grid items-stretch gap-8 py-10 md:grid-cols-2">
        {/* candidates */}
        <div id="candidates" className="flex scroll-mt-20 flex-col">
          <div className="min-h-[5.25rem]">
            <p className="text-sm text-muted">For candidates</p>
            <h2 className="mt-1 font-serif text-3xl leading-tight">Prove you can read code, not just write it</h2>
          </div>
          <div className="lift panel mt-6 flex flex-1 flex-col p-5">
            <div className="rounded-xl border border-line bg-white p-4">
              <p className="text-xs text-muted">Devsinc · Core SE · Associate</p>
              <pre className="mt-3 overflow-x-auto rounded-lg bg-ink p-3 text-[12.5px] leading-relaxed text-paper">
{`def has_pair_with_sum(nums, target):
    seen = []
    for n in nums:
        if target - n in seen:
            return True
        seen.append(n)
    return False`}
              </pre>
              <p className="mt-3 text-sm text-ink">What does this return, and what&apos;s its real time complexity?</p>
            </div>
            <div className="mt-auto flex items-center justify-between pt-4">
              <span className="text-sm text-muted">Comprehension</span>
              <span className="rounded-pill bg-ink px-3 py-1 text-sm font-semibold text-paper">Verify 82</span>
            </div>
          </div>
          <Link href="/signup" className="btn-dark mt-6 self-start">Start practising</Link>
        </div>

        {/* companies */}
        <div id="companies" className="flex scroll-mt-20 flex-col">
          <div className="min-h-[5.25rem]">
            <p className="text-sm text-muted">For companies</p>
            <h2 className="mt-1 font-serif text-3xl leading-tight">See who actually understands the code</h2>
          </div>
          <div className="lift panel mt-6 flex flex-1 flex-col p-5">
            <div className="space-y-2">
              {[
                { n: 'Ayesha K.', v: 88, flag: 'clean' },
                { n: 'Bilal R.', v: 81, flag: 'clean' },
                { n: 'Hamza S.', v: 74, flag: 'review' },
              ].map((c) => (
                <div key={c.n} className="flex items-center justify-between rounded-xl border border-line bg-white p-3.5">
                  <span className="text-sm font-medium text-ink">{c.n}</span>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-pill px-2.5 py-0.5 text-xs ${
                      c.flag === 'clean' ? 'bg-sand text-muted' : 'bg-brand/10 text-brand'
                    }`}>{c.flag === 'clean' ? 'integrity ✓' : 'needs review'}</span>
                    <span className="w-10 text-right font-semibold text-ink">{c.v}</span>
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-auto pt-4 text-xs text-muted">Ranked by verify score · integrity-adjusted</p>
          </div>
          <Link href="/signup" className="btn-ghost mt-6 self-start">Hire with asaanHire</Link>
        </div>
      </section>

      {/* ---- trusted-by strip (continuous slide) ---- */}
      <section className="py-14">
        <p className="wrap text-center text-sm text-muted">Modelled on how Pakistan&apos;s top tech teams hire</p>
        <div className="marquee mt-8">
          <div className="marquee-track gap-x-14">
            {[...COMPANIES, ...COMPANIES].map((c, i) => (
              <span key={i} className="shrink-0 whitespace-nowrap font-serif text-xl text-ink/55">{c}</span>
            ))}
          </div>
        </div>
      </section>

      <HowItWorks />
      <Footer />
    </>
  );
}
