const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
export async function api(path: string, init?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...init });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}
