// The bridge to the API. Same origin on the Space; VITE_API_BASE for a local server.
// Everything the app needs while offline lives in the SQLite file and localStorage;
// this module is only used when navigator.onLine says the network is there.

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';
const QUEUE_KEY = 'lifekit.questions';

export interface AnswerResult {
  answered: boolean;
  answer?: string;
  stored?: string;
  hits: { passage: string; title: string; edition: string; page: number; volume: string; text: string }[];
}

export interface Digest {
  answered: { id: string; question: string; answer: string; volumes: string[]; at: string; state: string }[];
  added: { id: string; title: string; publisher: string; retrieved: string; line: string }[];
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

export const answer = (question: string, tag?: string | null) => post<AnswerResult>('/api/answer', { question, tag: tag ?? null });
export const sync = () => post<{ digest: unknown[]; events: string[]; pending: unknown[] }>('/api/sync', {});
export const digest = async (): Promise<Digest> => (await fetch(`${BASE}/api/digest`)).json();

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
