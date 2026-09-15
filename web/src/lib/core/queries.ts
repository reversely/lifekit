// Every screen is one of these queries. No screen touches SQL directly.

import type { Database } from './db';
import { rows } from './db';
import { SECTIONS, type Hit, type Shelf, type SortKey, type Tag, type TagCount, type Volume } from './types';

const SORT_SQL: Record<SortKey, string> = {
  latest: 'v.retrieved DESC',
  oldest: 'v.retrieved ASC',
  title: 'v.title ASC',
  pages: 'v.page_count DESC',
};

const sectionTitle = (id: string) => SECTIONS.find((s) => s.id === id)?.title ?? id;

export function shelves(db: Database): Shelf[] {
  const counts = new Map(
    rows<{ tag: string; n: number }>(
      db,
      "SELECT t.tag AS tag, count(*) AS n FROM volume_tag t JOIN volume v ON v.id = t.volume_id WHERE v.carry = 'carry' AND v.page_count > 0 AND v.admission != 'rejected' AND t.tag LIKE 'section:%' GROUP BY t.tag",
    ).map((r) => [r.tag, r.n]),
  );
  return SECTIONS.map((s, i) => ({
    id: s.id,
    order: i + 1,
    title: s.title,
    scopeLine: s.scope,
    count: counts.get(`section:${s.id}`) ?? 0,
  }));
}

function tagsOf(db: Database, volumeId: string): Tag[] {
  return rows<{ tag: string; source: Tag['source'] }>(
    db,
    'SELECT tag, source FROM volume_tag WHERE volume_id = ? ORDER BY tag',
    [volumeId],
  ).map((r) => {
    const [namespace, value] = r.tag.split(/:(.+)/);
    return { tag: r.tag, namespace, value, source: r.source };
  });
}

export function volumes(db: Database, opts: { tag?: string; sort?: SortKey } = {}): Volume[] {
  const where = opts.tag ? ' AND v.id IN (SELECT volume_id FROM volume_tag WHERE tag = ?)' : '';
  const list = rows<any>(
    db,
    `SELECT v.id, v.title, v.publisher, v.edition, v.format, v.licence, v.page_count, v.retrieved, v.admission, c.text AS cover, c.digest_line
     FROM volume v LEFT JOIN cover c ON c.volume_id = v.id WHERE v.carry = 'carry' AND v.page_count > 0 AND v.admission != 'rejected'${where} ORDER BY ${SORT_SQL[opts.sort ?? 'latest']}`,
    opts.tag ? [opts.tag] : [],
  );
  return list.map((r) => ({
    id: r.id,
    title: r.title,
    publisher: r.publisher ?? '',
    edition: r.edition ?? '',
    format: r.format,
    licence: r.licence ?? '',
    pageCount: r.page_count ?? 0,
    retrieved: r.retrieved ?? '',
    cover: r.cover ?? '',
    digestLine: r.digest_line ?? '',
    admission: r.admission ?? 'stock',
    tags: tagsOf(db, r.id),
  }));
}

/** Tag counts for the filter groups, optionally within one section. */
export function tagCounts(db: Database, within?: string): TagCount[] {
  const scope = within ? ' AND v.id IN (SELECT volume_id FROM volume_tag WHERE tag = ?)' : '';
  const counts = rows<{ tag: string; n: number }>(
    db,
    `SELECT t.tag AS tag, count(*) AS n FROM volume_tag t JOIN volume v ON v.id = t.volume_id WHERE v.carry = 'carry' AND v.page_count > 0 AND v.admission != 'rejected'${scope} GROUP BY t.tag ORDER BY n DESC, t.tag`,
    within ? [`section:${within}`] : [],
  );
  const byTag = new Map(counts.map((c) => [c.tag, c.n]));
  const out: TagCount[] = [];
  // every section, in order, empty ones included
  for (const s of SECTIONS) {
    const tag = `section:${s.id}`;
    out.push({ tag, namespace: 'section', value: s.id, label: s.title, count: byTag.get(tag) ?? 0 });
  }
  for (const c of counts) {
    if (c.tag.startsWith('section:')) continue;
    const [namespace, value] = c.tag.split(/:(.+)/);
    out.push({ tag: c.tag, namespace, value, label: value, count: c.n });
  }
  return out;
}

const STOP = new Set(['the', 'and', 'for', 'how', 'can', 'what', 'with', 'you', 'are', 'should', 'who', 'someone', 'very', 'not', 'when', 'does', 'did', 'put', 'get', 'into', 'from', 'this', 'that', 'there', 'they', 'them', 'their', 'your', 'our', 'his', 'her', 'its', 'much', 'many']);
const ROLE_RANK: Record<string, number> = { primary: 0, reference: 0.5, depth: 0.7, figures: 1, archive: 2 };

function words(question: string): string[] {
  const all = question.toLowerCase().match(/[a-z0-9]+/g) ?? [];
  const kept = all.filter((w) => w.length > 2 && !STOP.has(w));
  return kept.length ? kept : all;
}

function ftsQueries(question: string): string[] {
  const w = words(question).map((x) => `"${x}"`);
  const queries = [w.join(' AND ')];
  if (w.length > 2) queries.push(w.map((drop) => `(${w.filter((x) => x !== drop).join(' AND ')})`).join(' OR '));
  queries.push(w.join(' OR '));
  return queries;
}

export function search(db: Database, question: string, opts: { tag?: string; limit?: number } = {}): Hit[] {
  const limit = opts.limit ?? 8;
  for (const query of ftsQueries(question)) {
    const hits = rows<any>(
      db,
      `SELECT f.passage_id AS passage, bm25(passage_fts) AS score, s.text, s.kind, p.number AS page, p.anchor,
              v.id AS volume, v.title, v.edition, sv.role
       FROM passage_fts f JOIN passage s ON s.id = f.passage_id JOIN page p ON p.id = s.page_id
       JOIN volume v ON v.id = p.volume_id JOIN shelf_volume sv ON sv.volume_id = v.id
       WHERE passage_fts MATCH ? AND v.admission != 'rejected' ORDER BY score LIMIT 60`,
      [query],
    )
      .filter((h) => !opts.tag || tagsOf(db, h.volume).some((t) => t.tag === opts.tag))
      .map((h) => ({
        ...h,
        score: h.score + (ROLE_RANK[h.role] ?? 1) - (['procedure_step', 'checklist', 'warning'].includes(h.kind) ? 1 : 0),
      }))
      .sort((a, b) => a.score - b.score)
      .slice(0, limit);
    if (hits.length >= Math.min(limit, 3)) return hits;
    if (query === ftsQueries(question).at(-1)) return hits;
  }
  return [];
}

/** Volumes whose title or cover matches the question's words. */
export function matchingVolumes(db: Database, question: string, limit = 3): Volume[] {
  const w = words(question);
  if (!w.length) return [];
  const like = w.map(() => '(lower(v.title) LIKE ? OR lower(c.text) LIKE ?)').join(' OR ');
  const params = w.flatMap((x) => [`%${x}%`, `%${x}%`]);
  const ids = rows<{ id: string }>(
    db,
    `SELECT v.id FROM volume v LEFT JOIN cover c ON c.volume_id = v.id WHERE v.carry = 'carry' AND v.page_count > 0 AND v.admission != 'rejected' AND (${like}) LIMIT ${limit}`,
    params,
  ).map((r) => r.id);
  return volumes(db).filter((v) => ids.includes(v.id));
}

export { sectionTitle };

export interface Page {
  id: string;
  number: number;
  anchor: string;
  text: string;
}

export function volume(db: Database, id: string): Volume | undefined {
  return volumes(db).find((v) => v.id === id);
}

export function volumeMeta(db: Database, id: string): { url: string; licence: string; statement: string; sha256: string; retrieved: string } | undefined {
  const r = rows<any>(db, 'SELECT url, licence, licence_statement, sha256, retrieved FROM volume WHERE id = ?', [id])[0];
  return r && { url: r.url, licence: r.licence, statement: r.licence_statement, sha256: r.sha256, retrieved: r.retrieved };
}

export function pageCount(db: Database, volumeId: string): number {
  return rows<{ n: number }>(db, 'SELECT count(*) AS n FROM page WHERE volume_id = ?', [volumeId])[0]?.n ?? 0;
}

export function page(db: Database, volumeId: string, number: number): Page | undefined {
  const r = rows<any>(db, 'SELECT id, number, anchor, text FROM page WHERE volume_id = ? AND number = ?', [volumeId, number])[0];
  return r && { id: r.id, number: r.number, anchor: r.anchor, text: r.text };
}

export function passagesOf(db: Database, pageId: string): { id: string; start: number; end: number; kind: string }[] {
  return rows<any>(db, 'SELECT id, start, "end" AS end, kind FROM passage WHERE page_id = ? ORDER BY start', [pageId]);
}

/** First-line headings of each page, for a contents outline. */
export function outline(db: Database, volumeId: string): { number: number; heading: string }[] {
  return rows<{ number: number; text: string }>(db, 'SELECT number, text FROM page WHERE volume_id = ? ORDER BY number', [volumeId]).map((r) => ({
    number: r.number,
    heading: (r.text.split('\n').find((l) => l.trim().length > 3) ?? '').slice(0, 80),
  }));
}
