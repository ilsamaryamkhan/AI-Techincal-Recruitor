'use client';
import { useEffect, useRef } from 'react';
// TODO [Ilsa+CV]: getUserMedia -> stream frames; run MediaPipe lightweight checks client-side,
// POST sampled frames to the proctoring service for the heavy checks.
export default function ProctorCam() {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      .then(s => { if (ref.current) ref.current.srcObject = s; }).catch(console.error);
  }, []);
  return <video ref={ref} autoPlay muted style={{ width: 240, borderRadius: 8 }} />;
}
