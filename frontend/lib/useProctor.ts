'use client';
import { useCallback, useRef, useState } from 'react';

/** Proctoring signals for a live interview.
 *
 *  Two kinds of signal:
 *   - Browser events (always reliable, no camera): tab hidden, window focus loss,
 *     paste, copy, right-click.
 *   - Camera (best-effort): face present? more than one face? via face-api.js
 *     loaded from a CDN. If the camera is denied or the model won't load, we fall
 *     back to event-only proctoring — the interview never breaks.
 *
 *  No video is recorded or uploaded. Only the derived signals (counts, flagged
 *  moments, a risk timeline, an integrity confidence) are sent to the server.
 */
const FACEAPI_SRC = 'https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js';
const MODEL_URL = 'https://cdn.jsdelivr.net/gh/justadudewhohacks/face-api.js@master/weights';
const TICK_MS = 1500;

type FaceState = 'ok' | 'no_face' | 'multiple_faces';
export type ProctorStatus = 'idle' | 'warming' | 'camera_off' | FaceState;
export type Incident = { t: number; type: string; severity: number; note: string };

export function useProctor() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [status, setStatus] = useState<ProctorStatus>('idle');
  const [cameraAvailable, setCameraAvailable] = useState(false);
  const [flags, setFlags] = useState(0);
  const [risk, setRisk] = useState(0);                 // live risk 0..100
  const [alert, setAlert] = useState<{ id: number; type: string; note: string } | null>(null);

  const riskRef = useRef(0);
  const incidentsRef = useRef<Incident[]>([]);
  const seriesRef = useRef<{ t: number; risk: number }[]>([]);
  const countsRef = useRef<Record<string, number>>({});
  const startedAt = useRef(0);
  const faceState = useRef<{ face: FaceState; segPoints: number }>({ face: 'ok', segPoints: 0 });
  const lastHidden = useRef(0);

  const streamRef = useRef<MediaStream | null>(null);
  const faceApiRef = useRef<any>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const detectingRef = useRef(false);
  const runningRef = useRef(false);
  const epochRef = useRef(0);   // invalidates in-flight start() across StrictMode remounts

  const elapsed = () => Math.round((Date.now() - startedAt.current) / 1000);

  const flashAlert = useCallback((type: string, note: string) => {
    setAlert({ id: Date.now() + Math.random(), type, note });
  }, []);

  const addIncident = useCallback((type: string, severity: number, note: string) => {
    riskRef.current = Math.min(100, riskRef.current + severity);
    incidentsRef.current.push({ t: elapsed(), type, severity, note });
    countsRef.current[type] = (countsRef.current[type] || 0) + 1;
    setFlags(incidentsRef.current.length);
    setRisk(Math.round(riskRef.current));
    flashAlert(type, note);
  }, [flashAlert]);

  // ---- browser event handlers ----
  const onVisibility = useCallback(() => {
    if (document.visibilityState === 'hidden') {
      lastHidden.current = Date.now();
      addIncident('tab_hidden', 18, 'Left the interview tab');
    } else if (lastHidden.current && Date.now() - lastHidden.current < 60000) {
      // they came back — surface the warning now that they can actually see it
      flashAlert('tab_hidden', 'You left the interview tab — this was recorded');
    }
  }, [addIncident, flashAlert]);
  const onBlur = useCallback(() => {
    if (Date.now() - lastHidden.current < 1200) return; // same action as tab hide
    addIncident('focus_loss', 10, 'Window lost focus');
  }, [addIncident]);
  const onPaste = useCallback(() => addIncident('paste', 25, 'Pasted text'), [addIncident]);
  const onCopy = useCallback(() => addIncident('copy', 8, 'Copied from the page'), [addIncident]);
  const onContext = useCallback(() => addIncident('context_menu', 4, 'Opened the right-click menu'), [addIncident]);

  const tick = useCallback(async () => {
    // always record a risk sample over time
    const faceapi = faceApiRef.current;
    const video = videoRef.current;
    if (faceapi && video && video.readyState >= 2 && !detectingRef.current) {
      detectingRef.current = true;
      try {
        const opts = new faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.5 });
        const res = await faceapi.detectAllFaces(video, opts);
        const count = res.length;
        const st: FaceState = count === 0 ? 'no_face' : count > 1 ? 'multiple_faces' : 'ok';
        const s = faceState.current;
        if (st !== s.face) {
          s.face = st; s.segPoints = 0;
          if (st === 'no_face') addIncident('no_face', 10, 'Face not visible');
          else if (st === 'multiple_faces') addIncident('multiple_faces', 30, `${count} people in frame`);
        } else if (st !== 'ok' && s.segPoints < 30) {
          const inc = st === 'multiple_faces' ? 6 : 3;
          riskRef.current = Math.min(100, riskRef.current + inc);
          s.segPoints += inc;
          setRisk(Math.round(riskRef.current));
        }
        setStatus(st);
      } catch { /* a dropped frame is fine */ }
      finally { detectingRef.current = false; }
    }
    seriesRef.current.push({ t: elapsed(), risk: Math.round(riskRef.current) });
  }, [addIncident]);

  async function loadFaceApi() {
    if ((window as any).faceapi?.nets?.tinyFaceDetector?.params) return (window as any).faceapi;
    if (!(window as any).faceapi) {
      await new Promise<void>((resolve, reject) => {
        const sc = document.createElement('script');
        sc.src = FACEAPI_SRC; sc.async = true;
        sc.onload = () => resolve(); sc.onerror = () => reject(new Error('face-api load failed'));
        document.head.appendChild(sc);
      });
    }
    const faceapi = (window as any).faceapi;
    await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
    return faceapi;
  }

  const beginTick = (myEpoch: number) => {
    if (myEpoch !== epochRef.current) return;
    if (tickRef.current) clearInterval(tickRef.current);
    tickRef.current = setInterval(tick, TICK_MS);
  };

  const start = useCallback(async () => {
    const myEpoch = ++epochRef.current;   // this run's identity; a later start/stop supersedes it
    runningRef.current = true;
    startedAt.current = Date.now();
    riskRef.current = 0; incidentsRef.current = []; seriesRef.current = []; countsRef.current = {};
    faceState.current = { face: 'ok', segPoints: 0 }; faceApiRef.current = null;
    setRisk(0); setAlert(null); setFlags(0); setCameraAvailable(false);

    // event listeners — always on, no camera needed
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('blur', onBlur);
    document.addEventListener('paste', onPaste);
    document.addEventListener('copy', onCopy);
    document.addEventListener('contextmenu', onContext);

    setStatus('warming');
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240 }, audio: false });
    } catch {
      if (myEpoch === epochRef.current) { setCameraAvailable(false); setStatus('camera_off'); }
      beginTick(myEpoch);
      return; // genuinely no camera — event-only proctoring
    }
    // a newer start() or a stop() ran while we were awaiting permission → discard this stream
    if (myEpoch !== epochRef.current) { stream.getTracks().forEach((t) => t.stop()); return; }

    streamRef.current = stream;
    const v = videoRef.current;
    if (v) {
      v.srcObject = stream;
      // the camera is "on" only once frames actually flow — this is what fixes the
      // false "camera off" when the stream is live but something else failed.
      v.onplaying = () => { if (myEpoch === epochRef.current) { setCameraAvailable(true); setStatus('ok'); } };
      try { await v.play(); } catch {}
      if (myEpoch === epochRef.current && v.readyState >= 2) { setCameraAvailable(true); setStatus('ok'); }
    } else if (myEpoch === epochRef.current) {
      setCameraAvailable(true); setStatus('ok');
    }
    // face model — NON-FATAL; camera stays on even if the CDN model can't load
    try { const fa = await loadFaceApi(); if (myEpoch === epochRef.current) faceApiRef.current = fa; }
    catch { if (myEpoch === epochRef.current) faceApiRef.current = null; }
    beginTick(myEpoch);
  }, [onVisibility, onBlur, onPaste, onCopy, onContext, tick]);

  const stop = useCallback(() => {
    epochRef.current++;   // invalidate any in-flight start()
    runningRef.current = false;
    if (tickRef.current) { clearInterval(tickRef.current); tickRef.current = null; }
    document.removeEventListener('visibilitychange', onVisibility);
    window.removeEventListener('blur', onBlur);
    document.removeEventListener('paste', onPaste);
    document.removeEventListener('copy', onCopy);
    document.removeEventListener('contextmenu', onContext);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, [onVisibility, onBlur, onPaste, onCopy, onContext]);

  const summary = useCallback(() => {
    const risk = Math.round(riskRef.current);
    return {
      integrity_confidence: Math.max(0, Math.min(1, 1 - risk / 100)),
      risk_score: risk,
      camera_available: cameraAvailable,
      flagged_segments: incidentsRef.current,
      counts: countsRef.current,
      risk_timeseries: seriesRef.current,
    };
  }, [cameraAvailable]);

  return { videoRef, status, cameraAvailable, flags, risk, alert, start, stop, summary };
}
