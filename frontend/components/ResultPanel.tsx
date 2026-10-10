'use client';

type Feedback = { obs_id: string; statement: string; required: boolean; covered: boolean };
type FW = { claim: string; contradicts: string };
export type PracticeResult = {
  scores: { verify_score: number; detection: number; explanation_quality: number;
            calibration: number; coverage_required: number; fluent_wrongness_count: number };
  feedback: Feedback[];
  fluent_wrongness: FW[];
  flagged_decoy: boolean;
  identified_core_issue: boolean;
  grounding_facts: string[];
  followup: string;
  graded_by: string;
};

function ring(score: number) {
  const tone = score >= 75 ? 'text-ink' : score >= 50 ? 'text-brand' : 'text-[#C8352B]';
  return tone;
}

export default function ResultPanel({ r, onRetry }: { r: PracticeResult; onRetry: () => void }) {
  const s = r.scores;
  return (
    <div className="space-y-6">
      {/* headline score */}
      <div className="panel flex items-center justify-between p-6">
        <div>
          <p className="text-sm text-muted">Verify score</p>
          <p className={`font-serif text-6xl leading-none ${ring(s.verify_score)}`}>{s.verify_score}</p>
          <p className="mt-2 text-sm text-muted">
            {r.identified_core_issue ? 'You identified the core issue.' : 'You missed the core issue.'}
            {' '}Graded by {r.graded_by === 'groq' ? 'AI grader' : 'offline grader'}.
          </p>
        </div>
        <div className="hidden gap-6 sm:flex">
          {[['Detection', s.detection], ['Explanation', s.explanation_quality], ['Calibration', s.calibration]].map(
            ([label, val]) => (
              <div key={label as string} className="text-center">
                <p className="font-serif text-2xl">{val}</p>
                <p className="text-xs text-muted">{label}</p>
              </div>
            ))}
        </div>
      </div>

      {/* fluent wrongness — the signal that matters most */}
      {r.fluent_wrongness.length > 0 && (
        <div className="rounded-2xl border border-[#EFC9C3] bg-[#FBECEA] p-5">
          <p className="text-sm font-semibold text-[#C8352B]">Confident but wrong</p>
          {r.fluent_wrongness.map((fw, i) => (
            <div key={i} className="mt-2 text-sm">
              <p className="text-ink">You claimed: <span className="italic">{fw.claim}</span></p>
              <p className="text-muted">The code says: {fw.contradicts}</p>
            </div>
          ))}
        </div>
      )}

      {r.flagged_decoy && (
        <div className="rounded-2xl border border-line bg-sand p-5 text-sm">
          <p className="font-semibold text-ink">Over-flagging cost you calibration</p>
          <p className="mt-1 text-muted">You flagged something that was actually correct. Reading code well means knowing when it&apos;s fine, not just when it&apos;s broken.</p>
        </div>
      )}

      {/* coverage checklist */}
      <div className="panel p-5">
        <p className="text-sm font-semibold text-ink">What a strong answer covers</p>
        <ul className="mt-3 space-y-2">
          {r.feedback.map((f) => (
            <li key={f.obs_id} className="flex items-start gap-2 text-sm">
              <span className={f.covered ? 'text-ink' : 'text-muted'}>{f.covered ? '✓' : '○'}</span>
              <span className={f.covered ? 'text-ink' : 'text-muted'}>
                {f.statement}{!f.required && <span className="text-muted"> (bonus)</span>}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* adaptive follow-up */}
      <div className="rounded-2xl border border-ink bg-ink p-5 text-paper">
        <p className="text-sm text-paper/70">Follow-up</p>
        <p className="mt-1 font-serif text-xl">{r.followup}</p>
      </div>

      <button onClick={onRetry} className="btn-ghost">Try another answer</button>
    </div>
  );
}
