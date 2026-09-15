// Opens library.sqlite in the browser through the official SQLite wasm build,
// which carries FTS5, so the browser runs the same search as the Python side.

import sqlite3InitModule, { type Database, type SqlValue } from '@sqlite.org/sqlite-wasm';

export type { Database, SqlValue };

let ready: Promise<Database> | null = null;
let generation = 0;

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
      const bytes = new Uint8Array(await (await fetch(`/library.sqlite?v=${generation}`, { cache: 'no-store' })).arrayBuffer());
      const pointer = sqlite3.wasm.allocFromTypedArray(bytes);
      const db = new sqlite3.oo1.DB();
      const rc = sqlite3.capi.sqlite3_deserialize(
        db.pointer!,
        'main',
        pointer,
        bytes.length,
        bytes.length,
        sqlite3.capi.SQLITE_DESERIALIZE_FREEONCLOSE | sqlite3.capi.SQLITE_DESERIALIZE_READONLY,
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
