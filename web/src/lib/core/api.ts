// The bridge to the API. Same origin on the Space; VITE_API_BASE for a local server.
// Everything the app needs while offline lives in the SQLite file and localStorage;
// this module is only used when navigator.onLine says the network is there.

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';
const QUEUE_KEY = 'lifekit.questions';

export interface AnswerResult {
  answered: boolean;
  answer?: string;
  stored?: string;
  topic?: string | null;
  wanted?: string | null;
  hits: { passage: string; title: string; edition: string; page: number; volume: string; text: string }[];
}

export interface Candidate {
  id: string;
  title: string;
  publisher: string;
  licence: string;
  retrieved: string;
  cover: string;
  section: string | null;
  question: { id: string; text: string; wanted: string | null; state: string; answer: string | null } | null;
}

export interface Pending {
  id: string;
  text: string;
  state: string;
  topic: string | null;
  origin: string;
}

export interface Digest {
  answered: { id: string; question: string; answer: string; volumes: string[]; at: string; state: string }[];
  added: { id: string; title: string; publisher: string; retrieved: string; line: string; admission: string }[];
  candidates: Candidate[];
  pending: Pending[];
}

export interface ProfileAnswers {
  country: string | null;
  region: string | null;
  terrain: string[];
  activities: string[];
  household: string[];
  trips: string[];
  updated_at: string | null;
}

export interface ProfileQuestion {
  key: keyof Omit<ProfileAnswers, 'updated_at'>;
  ask: string;
  multi: boolean;
  options: { value: string; label: string }[];
}

export interface Seeded {
  id: string;
  text: string;
  reason: string;
  rule: string;
}

export interface Profile {
  profile: ProfileAnswers;
  questions: ProfileQuestion[];
  summary: string;
  seeded?: Seeded[];
}

export interface Config {
  small: string;
  answer: string;
  loop: boolean;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

export const answer = (question: string, tag?: string | null) => post<AnswerResult>('/api/answer', { question, tag: tag ?? null });
export const sync = () => post<{ digest: unknown[]; events: string[]; pending: unknown[] }>('/api/sync', {});
export const digest = async (): Promise<Digest> => (await fetch(`${BASE}/api/digest`)).json();
export const config = async (): Promise<Config> => (await fetch(`${BASE}/api/config`)).json();
export const profile = async (): Promise<Profile> => (await fetch(`${BASE}/api/profile`)).json();
export const candidates = async (): Promise<{ candidates: Candidate[] }> => (await fetch(`${BASE}/api/candidates`)).json();
export const verdict = (volume: string, verdict: 'admit' | 'refile' | 'reject', section?: string | null) =>
  post<{ admission?: string; error?: string }>('/api/verdict', { volume, verdict, section: section ?? null });

export async function saveProfile(answers: Partial<Omit<ProfileAnswers, 'updated_at'>>): Promise<Profile> {
  const r = await fetch(`${BASE}/api/profile`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(answers) });
  if (!r.ok) throw new Error(`/api/profile: ${r.status}`);
  return r.json();
}

/** Questions asked while offline, kept in this browser until the network returns. */
export function queued(): { text: string; at: string }[] {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) ?? '[]');
  } catch {
    return [];
  }
}

export function enqueue(text: string): void {
  try {
    localStorage.setItem(QUEUE_KEY, JSON.stringify([...queued(), { text, at: new Date().toISOString() }]));
  } catch {
    /* storage unavailable: the question is shown as stored for this session only */
  }
}

/** Send every queued question to the server and clear the queue. */
export async function flush(): Promise<number> {
  const items = queued();
  for (const item of items) await post('/api/questions', { text: item.text });
  try {
    localStorage.removeItem(QUEUE_KEY);
  } catch {
    /* ignore */
  }
  return items.length;
}
