// Types the screens read. They mirror the tables in docs/content/library-schema.md.

export interface Shelf {
  id: string;
  order: number;
  title: string;
  scopeLine: string;
  icon: string;
  count: number;
}

export interface Volume {
  id: string;
  title: string;
  publisher: string;
  edition: string;
  format: 'pdf' | 'html' | 'image-set' | 'dataset';
  licence: string;
  pageCount: number;
  retrieved: string;
  cover: string;
  digestLine: string;
  admission: 'stock' | 'staged' | 'admitted' | 'rejected';
  tags: Tag[];
}

export interface Tag {
  tag: string;
  namespace: string;
  value: string;
  source: 'rule' | 'model' | 'hand';
}

export interface TagCount {
  tag: string;
  namespace: string;
  value: string;
  label: string;
  count: number;
}

export interface Hit {
  passage: string;
  text: string;
  kind: string;
  volume: string;
  title: string;
  edition: string;
  page: number;
  anchor: string;
  role: string;
  score: number;
}

export type SortKey = 'latest' | 'oldest' | 'title' | 'pages';


export const SORTS: { key: SortKey; label: string }[] = [
  { key: 'latest', label: 'Latest' },
  { key: 'oldest', label: 'Oldest' },
  { key: 'title', label: 'A to Z' },
  { key: 'pages', label: 'Pages' },
];
