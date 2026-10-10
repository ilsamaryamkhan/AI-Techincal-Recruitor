'use client';
import type { RefObject } from 'react';
import type { ProctorStatus } from '@/lib/useProctor';

const MAP: Record<ProctorStatus, { label: string; dot: string; text: string }> = {
  idle:            { label: 'Idle',               dot: 'bg-muted',    text: 'text-muted' },
  warming:         { label: 'Starting camera…',   dot: 'bg-muted animate-pulse', text: 'text-muted' },
  ok:              { label: 'Monitoring',          dot: 'bg-[#0A66F0]', text: 'text-ink' },
  no_face:         { label: 'Face not visible',    dot: 'bg-[#D69327]', text: 'text-[#9A6B12]' },
  multiple_faces:  { label: 'Multiple people',     dot: 'bg-[#C8352B]', text: 'text-[#C8352B]' },
  camera_off:      { label: 'Camera off · events only', dot: 'bg-muted', text: 'text-muted' },
};

export default function ProctorMonitor({
  videoRef, status, cameraAvailable, flags, risk,
}: {
  videoRef: RefObject<HTMLVideoElement | null>;
  status: ProctorStatus; cameraAvailable: boolean; flags: number; risk: number;
}) {
  const s = MAP[status] ?? MAP.idle;
  const level = risk >= 60 ? 'High' : risk >= 30 ? 'Elevated' : 'Low';
  const riskColor = risk >= 60 ? 'bg-[#C8352B]' : risk >= 30 ? 'bg-[#D69327]' : 'bg-[#0A66F0]';
  const riskText = risk >= 60 ? 'text-[#C8352B]' : risk >= 30 ? 'text-[#9A6B12]' : 'text-[#0A66F0]';
  return (
    <div className="fixed bottom-4 right-4 z-40 w-48 overflow-hidden rounded-2xl border border-line bg-white shadow-lg">
      <div className="relative aspect-[4/3] bg-ink">
        {/* video stays mounted so the proctor can attach the stream; mirrored like a selfie */}
        <video
          ref={videoRef as RefObject<HTMLVideoElement>} muted playsInline
          className={`h-full w-full object-cover ${cameraAvailable ? '' : 'opacity-0'}`}
          style={{ transform: 'scaleX(-1)' }}
        />
        {!cameraAvailable && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-paper/70">
            {status === 'warming' ? 'Starting camera…' : 'Camera off'}
          </div>
        )}
        {flags > 0 && (
          <span className="absolute right-1.5 top-1.5 rounded-pill bg-[#C8352B] px-2 py-0.5 text-[10px] font-semibold text-white">
            {flags} flag{flags === 1 ? '' : 's'}
          </span>
        )}
      </div>
      <div className="flex items-center gap-1.5 px-3 pt-2">
        <span className={`inline-block h-2 w-2 rounded-full ${s.dot}`} />
        <span className={`text-xs font-medium ${s.text}`}>{s.label}</span>
      </div>
      {/* live risk meter */}
      <div className="px-3 pb-2.5 pt-1.5">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-muted">Risk</span>
          <span className={`font-semibold ${riskText}`}>{level} · {risk}</span>
        </div>
        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-pill bg-sand">
          <div className={`h-full rounded-pill transition-all duration-500 ${riskColor}`} style={{ width: `${risk}%` }} />
        </div>
      </div>
    </div>
  );
}
