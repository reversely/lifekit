// Types the screens read. They mirror the tables in docs/content/library-schema.md.

export interface Shelf {
  id: string;
  order: number;
  title: string;
  scopeLine: string;
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

export const SECTIONS: { id: string; title: string; scope: string }[] = [
  { id: 'medicine', title: 'Survival Medicine', scope: 'Lifesaving steps, injuries, bites and stings, wounds' },
  { id: 'shelter', title: 'Shelter', scope: 'Site selection and shelter builds' },
  { id: 'fire', title: 'Fire', scope: 'Site preparation, materials, fire lays, ignition' },
  { id: 'water', title: 'Water', scope: 'Sources, stills, purification, filtration, crossings' },
  { id: 'food', title: 'Food', scope: 'Traps, snares, fishing, game preparation, edible plants' },
  { id: 'poisonous-plants', title: 'Poisonous Plants', scope: 'Poisoning routes, avoidance rules, deadly lookalikes' },
  { id: 'animals', title: 'Dangerous Animals', scope: 'Insects, arachnids, snakes, aquatic dangers' },
  { id: 'tools', title: 'Tools & Cordage', scope: 'Lashing, cordage, knots, improvised tools' },
  { id: 'direction', title: 'Direction Finding', scope: 'Celestial methods, improvised compass, offline map' },
  { id: 'signaling', title: 'Signaling & Rescue', scope: 'Signals, codes, ground-air signals, aircraft vectoring' },
  { id: 'environments', title: 'Environments', scope: 'Desert, tropical, cold weather, and sea modules' },
  { id: 'hazards', title: 'Man-Made Hazards', scope: 'Shielding, decontamination, protected water, chemical release' },
];

export const SORTS: { key: SortKey; label: string }[] = [
  { key: 'latest', label: 'Latest' },
  { key: 'oldest', label: 'Oldest' },
  { key: 'title', label: 'A to Z' },
  { key: 'pages', label: 'Pages' },
];
