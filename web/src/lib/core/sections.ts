// The twelve sections, read from the shelf table the build writes from packs/sections.tsv.
// No screen names a section in code; every list, title, and icon comes from here.

import type { Database } from './db';
import { rows } from './db';

export interface SectionRow {
  id: string;
  order: number;
  title: string;
  scope: string;
  icon: string;
  gloss: string;
  accent: string | null;
}

const cache = new WeakMap<Database, SectionRow[]>();

/** Every section in order, memoised per database instance. */
export function sections(db: Database): SectionRow[] {
  let list = cache.get(db);
  if (!list) {
    const cols = rows<{ name: string }>(db, 'PRAGMA table_info(shelf)').map((c) => c.name);
    const accent = cols.includes('accent') ? 'accent' : 'NULL AS accent';
    list = rows<{ id: string; order: number; title: string; scope_line: string | null; icon: string | null; gloss: string | null; accent: string | null }>(
      db,
      `SELECT id, "order" AS "order", title, scope_line, icon, gloss, ${accent} FROM shelf ORDER BY "order"`,
    ).map((r) => ({ id: r.id, order: r.order, title: r.title, scope: r.scope_line ?? '', icon: r.icon ?? 'book-open', gloss: r.gloss ?? '', accent: r.accent ?? null }));
    cache.set(db, list);
  }
  return list;
}

export function sectionTitle(db: Database, id: string): string {
  return sections(db).find((s) => s.id === id)?.title ?? id;
}
