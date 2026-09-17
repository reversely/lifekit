// Chat threads, carried over from the flux app's chat store: every thread persists in
// this browser, newest first; a send appends a user turn and a pending assistant turn,
// then the answer fills it. Offline, the question is stored for the loop instead.

import { writable, get } from 'svelte/store';
import { enqueue } from './api';

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';
const KEY = 'lifekit.chats';

export interface ChatSource {
  title: string;
  edition: string;
  volume: string;
  page: number;
  passage: string;
  snippet: string;
}
export interface ChatQueued {
  id: string;
  topic: string;
  wanted: string | null;
}
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  sources?: ChatSource[];
  queued?: ChatQueued | null;
  stored?: boolean;
  pending?: boolean;
}
export interface ChatThread {
  id: string;
  title: string;
  startedAt: string;
  messages: ChatMessage[];
}

let next = 0;
const id = (prefix: string) => `${prefix}${Date.now().toString(36)}_${++next}`;

function load(): ChatThread[] {
  try {
    const threads: ChatThread[] = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    for (const t of threads) t.messages = t.messages.filter((m) => !m.pending);
    return threads;
  } catch {
    return [];
  }
}
function persist(threads: ChatThread[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(threads));
  } catch {
    /* storage unavailable */
  }
}

export const threads = writable<ChatThread[]>(load());
export const activeId = writable<string | null>(null);
threads.subscribe(persist);

export function open(threadId: string) {
  if (get(threads).some((t) => t.id === threadId)) activeId.set(threadId);
}
export function startNew() {
  activeId.set(null);
}

/** Send one question on the active thread, starting one when none is active. */
export async function send(question: string, online: boolean): Promise<void> {
  const trimmed = question.trim();
  if (!trimmed) return;
  let threadId = get(activeId);
  if (!threadId || !get(threads).some((t) => t.id === threadId)) {
    threadId = id('t');
    threads.update((all) => [{ id: threadId!, title: trimmed.slice(0, 80), startedAt: new Date().toISOString(), messages: [] }, ...all]);
    activeId.set(threadId);
  }
  const pendingId = id('m');
  const patch = (fn: (t: ChatThread) => ChatThread) => threads.update((all) => all.map((t) => (t.id === threadId ? fn(t) : t)));
  patch((t) => ({ ...t, messages: [...t.messages, { id: id('m'), role: 'user', text: trimmed }, { id: pendingId, role: 'assistant', text: '', pending: true }] }));
  const fill = (m: Partial<ChatMessage>) => patch((t) => ({ ...t, messages: t.messages.map((x) => (x.id === pendingId ? { ...x, ...m, pending: false } : x)) }));
  if (!online) {
    enqueue(trimmed);
    fill({ text: 'Offline. Stored until the network returns.', stored: true });
    return;
  }
  const thread = get(threads).find((t) => t.id === threadId)!;
  const history = thread.messages.filter((m) => !m.pending && m.id !== pendingId).slice(-9, -1).map((m) => ({ role: m.role, text: m.text }));
  try {
    const r = await fetch(`${BASE}/api/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: trimmed, history }) });
    if (!r.ok) throw new Error(`chat: ${r.status}`);
    const a = await r.json();
    fill({ text: a.text, sources: a.sources, queued: a.queued });
  } catch {
    enqueue(trimmed);
    fill({ text: 'Model unreachable. Stored until the model returns.', stored: true });
  }
}
