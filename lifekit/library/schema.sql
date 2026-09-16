-- The library, per docs/content/library-schema.md. Prototype subset for one shelf.

CREATE TABLE IF NOT EXISTS shelf (
    id TEXT PRIMARY KEY,
    "order" INTEGER NOT NULL,
    title TEXT NOT NULL,
    scope_line TEXT,
    icon TEXT,
    gloss TEXT
);

CREATE TABLE IF NOT EXISTS volume (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    publisher TEXT,
    edition TEXT,
    url TEXT,
    format TEXT,
    licence TEXT,
    licence_statement TEXT,
    licence_read_at TEXT,
    retrieved TEXT,
    sha256 TEXT,
    carry TEXT NOT NULL CHECK (carry IN ('carry', 'link')),
    tier TEXT NOT NULL DEFAULT 'core',
    language TEXT DEFAULT 'en',
    page_count INTEGER,
    freshness TEXT DEFAULT 'static',
    live_source TEXT,
    superseded_by TEXT,
    -- docs/content/deployments-and-approval.md 3.1: stock from a shelf list; staged by the
    -- loop awaiting the owner's verdict; admitted; rejected (hidden from search).
    admission TEXT NOT NULL DEFAULT 'stock' CHECK (admission IN ('stock', 'staged', 'admitted', 'rejected')),
    admitted_at TEXT,
    admitted_by TEXT
);

CREATE TABLE IF NOT EXISTS shelf_volume (
    shelf_id TEXT REFERENCES shelf(id),
    volume_id TEXT REFERENCES volume(id),
    "order" INTEGER,
    role TEXT CHECK (role IN ('primary', 'reference', 'figures', 'archive', 'depth')),
    PRIMARY KEY (shelf_id, volume_id)
);

CREATE TABLE IF NOT EXISTS page (
    id TEXT PRIMARY KEY,
    volume_id TEXT REFERENCES volume(id),
    number INTEGER,
    anchor TEXT,
    text TEXT NOT NULL,
    render TEXT
);

CREATE TABLE IF NOT EXISTS passage (
    id TEXT PRIMARY KEY,
    page_id TEXT REFERENCES page(id),
    start INTEGER NOT NULL,
    "end" INTEGER NOT NULL,
    text TEXT NOT NULL,
    kind TEXT NOT NULL,
    topics TEXT DEFAULT '[]',
    scope_id TEXT DEFAULT 'universal',
    data TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS passage_fts USING fts5(
    text, passage_id UNINDEXED, tokenize = 'porter unicode61'
);

CREATE TABLE IF NOT EXISTS provenance (
    entity_id TEXT,
    activity TEXT,
    agent TEXT,
    derived_from TEXT,
    at TEXT
);

CREATE TABLE IF NOT EXISTS rag_test (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    expected_passages TEXT NOT NULL,
    origin TEXT,
    last_run TEXT,
    last_pass INTEGER
);

-- Tags: many per volume. The twelve sections are tags in the "section" namespace;
-- any other namespace is allowed. source says who set it: rule, model, or hand.
CREATE TABLE IF NOT EXISTS volume_tag (
    volume_id TEXT REFERENCES volume(id),
    tag TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'rule' CHECK (source IN ('rule', 'model', 'hand')),
    at TEXT,
    PRIMARY KEY (volume_id, tag)
);

-- Stored questions and the digest the loop writes (docs/content/library-schema.md 1.9).
-- topic and wanted form the gap record (deployments-and-approval.md 2); origin says who
-- asked: 'asked' for the reader, or the pull rule id that seeded it from the profile.
CREATE TABLE IF NOT EXISTS question (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    profile_snapshot TEXT,
    asked_at TEXT,
    state TEXT NOT NULL DEFAULT 'stored',
    topic TEXT,
    wanted TEXT,
    origin TEXT NOT NULL DEFAULT 'asked',
    answer_passages TEXT
);
-- One household per instance: the owner's answers, one row, json per column.
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    country TEXT,
    region TEXT,
    terrain TEXT DEFAULT '[]',
    activities TEXT DEFAULT '["home"]',
    household TEXT DEFAULT '["adult"]',
    trips TEXT DEFAULT '[]',
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS digest (
    question_id TEXT PRIMARY KEY,
    answer TEXT,
    volumes TEXT,
    at TEXT
);
