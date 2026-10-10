'use client';
import { useMemo, useState } from 'react';

// Invite a candidate to a Google Meet — no API keys, no login wall.
// We build a pre-filled Google Calendar event link: the recruiter picks a time,
// Google Calendar opens with the interview, the candidate added as a guest, and
// one click to "Add Google Meet" + Save sends the invite with a Meet link.

function pad(n: number) { return n.toString().padStart(2, '0'); }
// a Date -> Google's basic UTC format: YYYYMMDDTHHMMSSZ
function gcalStamp(d: Date) {
  return (
    d.getUTCFullYear().toString() + pad(d.getUTCMonth() + 1) + pad(d.getUTCDate()) + 'T' +
    pad(d.getUTCHours()) + pad(d.getUTCMinutes()) + '00Z'
  );
}
function tomorrowDate() {
  const d = new Date(); d.setDate(d.getDate() + 1);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export default function MeetScheduler({ name, email }: { name: string; email: string }) {
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState(tomorrowDate());
  const [time, setTime] = useState('16:00');
  const [mins, setMins] = useState(45);
  const [copied, setCopied] = useState(false);

  const calUrl = useMemo(() => {
    if (!date || !time) return '';
    const start = new Date(`${date}T${time}`);
    if (isNaN(start.getTime())) return '';
    const end = new Date(start.getTime() + mins * 60000);
    const title = `asaanHire interview — ${name}`;
    const details =
      `Code-comprehension interview via asaanHire.\n\n` +
      `When this event opens, click “Add Google Meet video conferencing”, then Save — ` +
      `${email} will be invited with the Meet link.`;
    const p = new URLSearchParams({
      action: 'TEMPLATE',
      text: title,
      dates: `${gcalStamp(start)}/${gcalStamp(end)}`,
      details,
      add: email,
    });
    return `https://calendar.google.com/calendar/render?${p.toString()}`;
  }, [date, time, mins, name, email]);

  const niceWhen = useMemo(() => {
    if (!date || !time) return '';
    const start = new Date(`${date}T${time}`);
    if (isNaN(start.getTime())) return '';
    return start.toLocaleString(undefined, {
      weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
    });
  }, [date, time]);

  async function copyLink() {
    try { await navigator.clipboard.writeText(calUrl); setCopied(true); setTimeout(() => setCopied(false), 1800); } catch {}
  }

  return (
    <div className="mt-6 rounded-2xl border border-line bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-serif text-lg text-ink">Move forward with {name.split(' ')[0]}</p>
          <p className="mt-0.5 text-sm text-muted">Invite them to a Google Meet interview.</p>
        </div>
        <button onClick={() => setOpen((v) => !v)} className={open ? 'btn-ghost' : 'btn-dark'}>
          {open ? 'Close' : 'Schedule a Google Meet'}
        </button>
      </div>

      {open && (
        <div className="mt-5 border-t border-line pt-5">
          <div className="grid gap-3 sm:grid-cols-[1fr_1fr_160px]">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-ink">Date</span>
              <input type="date" className="field" value={date} onChange={(e) => setDate(e.target.value)} />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-ink">Start time</span>
              <input type="time" className="field" value={time} onChange={(e) => setTime(e.target.value)} />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-ink">Duration</span>
              <select className="field" value={mins} onChange={(e) => setMins(Number(e.target.value))}>
                <option value={30}>30 min</option>
                <option value={45}>45 min</option>
                <option value={60}>60 min</option>
              </select>
            </label>
          </div>

          <p className="mt-3 text-sm text-muted">
            Invites <span className="text-ink">{email}</span>{niceWhen ? <> · <span className="text-ink">{niceWhen}</span></> : null}.
            Google Calendar opens pre-filled — add Meet and hit Save to send.
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <a
              href={calUrl || undefined}
              target="_blank"
              rel="noopener noreferrer"
              className={`btn-dark ${calUrl ? '' : 'pointer-events-none opacity-50'}`}
            >
              Open Google Calendar invite →
            </a>
            <button onClick={copyLink} disabled={!calUrl} className="btn-ghost">
              {copied ? 'Link copied' : 'Copy invite link'}
            </button>
            <a href="https://meet.google.com/new" target="_blank" rel="noopener noreferrer"
               className="text-sm text-brand hover:underline">
              or start an instant Meet
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
