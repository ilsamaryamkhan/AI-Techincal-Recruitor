const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const TOKEN_KEY = 'asaanhire_token';
const ROLE_KEY = 'asaanhire_role';

export function saveAuth(token: string, role: string) {
  try { localStorage.setItem(TOKEN_KEY, token); localStorage.setItem(ROLE_KEY, role); } catch {}
}
export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function getRole(): string | null {
  try { return localStorage.getItem(ROLE_KEY); } catch { return null; }
}
export function clearAuth() {
  try { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(ROLE_KEY); } catch {}
}

export async function api(path: string, init: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(init.headers as any) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = `${res.status}`;
    try { detail = (await res.json()).detail ?? detail; } catch {}
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

// typed helpers
export const login = (email: string, password: string) =>
  api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });

export const register = (body: Record<string, unknown>) =>
  api('/auth/register', { method: 'POST', body: JSON.stringify(body) });

export const listCompanies = () => api('/companies');
export const listItems = (q = '') => api(`/items${q}`);
export const getItem = (id: string) => api(`/items/${id}`);
export const submitPractice = (item_id: string, explanation: string) =>
  api('/practice/submit', { method: 'POST', body: JSON.stringify({ item_id, explanation }) });

// recruiter dashboard
export const recruiterStats = () => api('/recruiter/stats');
export const recruiterCandidates = (query = '') => api(`/recruiter/candidates${query}`);
export const recruiterCandidate = (id: number | string) => api(`/recruiter/candidates/${id}`);

// live interview
export const startInterview = (body: { domain?: string; level?: string }) =>
  api('/interview/start', { method: 'POST', body: JSON.stringify(body) });
export const answerInterview = (sid: string, transcript: string) =>
  api(`/interview/${sid}/answer`, { method: 'POST', body: JSON.stringify({ transcript }) });
export const postProctor = (sid: string, summary: Record<string, unknown>) =>
  api(`/interview/${sid}/proctor`, { method: 'POST', body: JSON.stringify(summary) });

// company test authoring
export const companyItems = () => api('/company/items');
// generate a draft from an uploaded document (multipart — don't set Content-Type)
export async function generateCompanyItem(form: FormData) {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BASE}/company/generate`, { method: 'POST', body: form, headers });
  if (!res.ok) {
    let detail = `${res.status}`;
    try { detail = (await res.json()).detail ?? detail; } catch {}
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${res.status})`);
  }
  return res.json();
}
export const verifyCompanyItem = (draft: Record<string, unknown>) =>
  api('/company/items/verify', { method: 'POST', body: JSON.stringify(draft) });
export const createCompanyItem = (draft: Record<string, unknown>) =>
  api('/company/items', { method: 'POST', body: JSON.stringify(draft) });
export const deleteCompanyItem = (id: string) =>
  api(`/company/items/${id}`, { method: 'DELETE' });
