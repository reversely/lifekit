// Opens library.sqlite in the browser through the official SQLite wasm build,
// which carries FTS5, so the browser runs the same search as the Python side.

import sqlite3InitModule, { type Database, type SqlValue } from '@sqlite.org/sqlite-wasm';
import { writable } from 'svelte/store';
import { headers } from './api';

export type { Database, SqlValue };

let ready: Promise<Database> | null = null;
let generation = 0;

/** Bytes received and expected while the database downloads, for the loading line. */
export const loading = writable<{ received: number; total: number; cached: boolean }>({ received: 0, total: 0, cached: false });

// The browser keeps the last downloaded database in IndexedDB with the server's
// Last-Modified stamp, so a reopened page downloads it again only when it changed.
const STORE = 'lifekit-db';
function idb(): Promise<IDBDatabase | null> {
  return new Promise((resolve) => {
    try {
      const request = indexedDB.open(STORE, 1);
      request.onupgradeneeded = () => request.result.createObjectStore('files');
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}
async function kept(): Promise<{ stamp: string; bytes: Uint8Array } | null> {
  const db = await idb();
  if (!db) return null;
  return new Promise((resolve) => {
    const request = db.transaction('files').objectStore('files').get('library');
    request.onsuccess = () => resolve(request.result ?? null);
    request.onerror = () => resolve(null);
  });
}
async function keep(stamp: string, bytes: Uint8Array): Promise<void> {
  const db = await idb();
  if (!db) return;
  await new Promise<void>((resolve) => {
    const tx = db.transaction('files', 'readwrite');
    tx.objectStore('files').put({ stamp, bytes }, 'library');
    tx.oncomplete = () => resolve();
    tx.onerror = () => resolve();
  });
}

/** The database bytes: the kept copy when the server's stamp matches, else a download with progress. */
async function fetchBytes(): Promise<Uint8Array> {
  const response = await fetch(`/library.sqlite?v=${generation}`, { cache: 'no-store', headers: headers() });
  if (!response.ok || !response.body) throw new Error(`library.sqlite: ${response.status}`);
  const stamp = `${response.headers.get('last-modified') ?? ''}|${response.headers.get('content-length') ?? ''}`;
  const total = Number(response.headers.get('content-length') ?? 0);
  const saved = await kept();
  if (saved && saved.stamp === stamp && stamp !== '|') {
    await response.body.cancel();
    loading.set({ received: saved.bytes.length, total: saved.bytes.length, cached: true });
    return saved.bytes;
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let received = 0;
  loading.set({ received: 0, total, cached: false });
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    chunks.push(value);
    received += value.length;
    loading.set({ received, total, cached: false });
  }
  const bytes = new Uint8Array(received);
  let at = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, at);
    at += chunk.length;
  }
  if (stamp !== '|') void keep(stamp, bytes);
  return bytes;
}

/** Drop the cached database and fetch the file again (after a sync or a verdict). */
export function reload(): Promise<Database> {
  ready = null;
  generation += 1;
  return database();
}

export function database(): Promise<Database> {
  if (!ready) {
    ready = (async () => {
      const sqlite3 = await sqlite3InitModule();
      const bytes = await fetchBytes();
      const pointer = sqlite3.wasm.allocFromTypedArray(bytes);
      const db = new sqlite3.oo1.DB();
      const rc = sqlite3.capi.sqlite3_deserialize(
        db.pointer!,
        'main',
        pointer,
        bytes.length,
        bytes.length,
        sqlite3.capi.SQLITE_DESERIALIZE_FREEONCLOSE,
      );
      if (rc !== 0) throw new Error(`sqlite3_deserialize failed with ${rc}`);
      return db;
    })();
  }
  return ready;
}

/** Run a query and return rows as objects keyed by column name. */
export function rows<T = Record<string, SqlValue>>(db: Database, sql: string, params: SqlValue[] = []): T[] {
  return db.selectObjects(sql, params as any) as T[];
}

/** Mirror a verdict the API applied into the in-memory copy, so the screens change
 *  at once instead of waiting for the file to download again. */
export function applyVerdict(db: Database, volumeId: string, admission: string, section: string | null): void {
  db.exec({ sql: 'UPDATE volume SET admission = ? WHERE id = ?', bind: [admission, volumeId] });
  if (section) {
    db.exec({ sql: 'DELETE FROM shelf_volume WHERE volume_id = ?', bind: [volumeId] });
    db.exec({ sql: "INSERT INTO shelf_volume VALUES (?, ?, (SELECT coalesce(max(\"order\"), 0) + 1 FROM shelf_volume WHERE shelf_id = ?), 'reference')", bind: [section, volumeId, section] });
    db.exec({ sql: "DELETE FROM volume_tag WHERE volume_id = ? AND tag LIKE 'section:%'", bind: [volumeId] });
    db.exec({ sql: "INSERT OR REPLACE INTO volume_tag VALUES (?, ?, 'hand', '')", bind: [volumeId, `section:${section}`] });
  }
  dispatchEvent(new CustomEvent('lifekit:changed'));
}
