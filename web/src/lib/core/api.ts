// The bridge to the API. Same origin on the Space; VITE_API_BASE for a local server.
// Everything the app needs while offline lives in the SQLite file and localStorage;
// this module is only used when navigator.onLine says the network is there.

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';

/** The box token (localStorage lifekit.token) rides every request; a test run also marks
 *  its requests (lifekit.test) so the API records nothing it does as a reader's choice. */
export function headers(extra: Record<string, string> = {}): Record<string, string> {
  const h: Record<string, string> = { ...extra };
  try {
    const token = localStorage.getItem('lifekit.token');
    if (token) h['X-LifeKit-Token'] = token;
    if (localStorage.getItem('lifekit.test') === '1') h['X-LifeKit-Test'] = '1';
  } catch {
    /* storage unavailable */
  }
  return h;
}

/** fetch with the headers above; a 401 tells the app to ask for the token. */
export async function api(path: string, init: RequestInit = {}): Promise<Response> {
  const r = await fetch(`${BASE}${path}`, { ...init, headers: { ...headers(), ...(init.headers as Record<string, string> | undefined) } });
  if (r.status === 401) dispatchEvent(new CustomEvent('lifekit:token'));
  return r;
}
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
  online_retrieval: boolean;
  zim?: { file: string; articles: number } | null;
  sections?: { id: string; order: number; title: string; scope: string; gloss: string; icon: string }[];
  questions?: Record<string, string[]>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

export const answer = (question: string, tag?: string | null) => post<AnswerResult>('/api/answer', { question, tag: tag ?? null });
export const sync = () => post<{ digest: unknown[]; events: string[]; pending: unknown[] }>('/api/sync', {});
export const digest = async (): Promise<Digest> => (await api('/api/digest')).json();
export const config = async (): Promise<Config> => (await api('/api/config')).json();
export const profile = async (): Promise<Profile> => (await api('/api/profile')).json();
export const candidates = async (): Promise<{ candidates: Candidate[] }> => (await api('/api/candidates')).json();
export const verdict = (volume: string, verdict: 'admit' | 'refile' | 'reject', section?: string | null) =>
  post<{ admission?: string; error?: string }>('/api/verdict', { volume, verdict, section: section ?? null });

export async function saveProfile(answers: Partial<Omit<ProfileAnswers, 'updated_at'>>): Promise<Profile> {
  const r = await api('/api/profile', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(answers) });
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

/** One record per online retrieval step, as the server emits it. */
export interface RetrievalEvent {
  id?: number;
  question: string;
  step: string;
  at: string;
  text?: string;
  origin?: string;
  topic?: string;
  source?: string;
  titles?: string[];
  section?: string;
  volume?: string;
  title?: string;
  volumes?: string[];
  answer?: string;
  pages?: { title: string; page: number; volume: string; passage: string }[];
  reason?: string;
  error?: string;
  done?: boolean;
  note?: string;
}

/** Run the online retrieval and receive each step as it happens. Resolves when the pass ends. */
export async function syncStream(onEvent: (e: RetrievalEvent) => void): Promise<RetrievalEvent | null> {
  const r = await api('/api/sync/stream', { cache: 'no-store' });
  if (!r.ok || !r.body) throw new Error(`sync: ${r.status}`);
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let last: RetrievalEvent | null = null;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let index;
    while ((index = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, index).trim();
      buffer = buffer.slice(index + 1);
      if (!line) continue;
      const event = JSON.parse(line) as RetrievalEvent;
      last = event;
      onEvent(event);
    }
  }
  return last;
}

/** The event log: every step of online retrieval, however the run started, after `since`. */
export async function events(since = 0): Promise<RetrievalEvent[]> {
  const r = await api(`/api/events?since=${since}`, { cache: 'no-store' });
  if (!r.ok) return [];
  return (await r.json()).events as RetrievalEvent[];
}
