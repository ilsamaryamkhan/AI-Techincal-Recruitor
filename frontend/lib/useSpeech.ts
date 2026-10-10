'use client';
import { useEffect, useRef, useState } from 'react';

/** Thin wrapper over the browser SpeechRecognition API (Chrome/Edge).
 *  Calls onFinal with each finalized chunk so the caller appends it to the
 *  answer box; the box stays fully editable with the keyboard as the fallback. */
export function useSpeech(onFinal: (text: string) => void) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const recRef = useRef<any>(null);
  const onFinalRef = useRef(onFinal);
  onFinalRef.current = onFinal;

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { setSupported(false); return; }
    setSupported(true);
    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = false;
    rec.lang = 'en-US';
    rec.onresult = (e: any) => {
      let chunk = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) chunk += e.results[i][0].transcript;
      }
      if (chunk.trim()) onFinalRef.current(chunk.trim() + ' ');
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    return () => { try { rec.stop(); } catch {} };
  }, []);

  function start() {
    if (!recRef.current || listening) return;
    try { recRef.current.start(); setListening(true); } catch {}
  }
  function stop() {
    if (!recRef.current) return;
    try { recRef.current.stop(); } catch {}
    setListening(false);
  }
  return { supported, listening, start, stop };
}
