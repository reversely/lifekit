<script lang="ts">
  import type { Database } from '../core/db';
  import { outline, page, pageCount, passagesOf, volume, volumeMeta } from '../core/queries';
  import { SECTIONS } from '../core/types';
  export let db: Database;
  export let id: string;
  export let initialPage = 1;
  export let highlight: string | null = null;

  $: v = volume(db, id);
  $: meta = volumeMeta(db, id);
  $: total = pageCount(db, id);
  let current = initialPage;
  $: current = initialPage;
  $: p = page(db, id, current);
  $: passages = p ? passagesOf(db, p.id) : [];
  $: contents = v?.format === 'html' ? outline(db, id) : [];
  const sectionsOf = (tags: { tag: string }[]) =>
    tags.filter((t) => t.tag.startsWith('section:')).map((t) => SECTIONS.find((s) => s.id === t.tag.slice(8))?.title ?? t.tag);

  /** Page text split into passages, so the one arrived at from search can be marked. */
  $: pieces = p
    ? passages.map((s) => ({ id: s.id, kind: s.kind, text: p!.text.slice(s.start, s.end), hit: s.id === highlight }))
    : [];
</script>

{#if v}
  <div class="screen">
    <div class="top">
      <a class="back" href="#/recent">‹ Recent</a>
      <h1 class="vol-title">{v.title}</h1>
      <span class="sub">{v.publisher}, {v.edition}</span>
    </div>
    <div class="vol-head">
      <img class="thumb big" src={`/thumbs/${v.id}.png`} alt="" />
      <div>
        <p class="cover">{v.cover}</p>
        <div class="tags">
          {#each sectionsOf(v.tags) as s}<span class="tag section">{s}</span>{/each}
          {#each v.tags.filter((t) => t.namespace !== 'section') as t}<span class="tag" class:hand={t.source === 'hand'}>{t.value}</span>{/each}
        </div>
        <div class="meta">
          <div>{total} pages, {v.licence}</div>
          {#if meta?.statement}<div class="quote">“{meta.statement}”</div>{/if}
          <div>Retrieved {(meta?.retrieved ?? '').slice(0, 10)}, sha256 {(meta?.sha256 ?? '').slice(0, 12)}</div>
          <a class="open" href={meta?.url} target="_blank" rel="noreferrer">Open the original</a>
        </div>
      </div>
    </div>

    {#if contents.length > 1}
      <div class="group">Contents</div>
      <div class="contents">
        {#each contents as c}
          <button class="line" class:on={c.number === current} on:click={() => (current = c.number)}>{c.heading}</button>
        {/each}
      </div>
    {/if}

    <div class="pager">
      <button class="chip" disabled={current <= 1} on:click={() => (current = current - 1)}>‹</button>
      <span>Page {current} of {total}</span>
      <button class="chip" disabled={current >= total} on:click={() => (current = current + 1)}>›</button>
    </div>
    {#if p}
      <div class="page">
        {#each pieces as piece}
          <p class="passage" class:hit={piece.hit} class:warning={piece.kind === 'warning'}>{piece.text}</p>
        {/each}
      </div>
    {/if}
  </div>
{:else}
  <div class="screen"><div class="top"><h1>Not in the library</h1></div></div>
{/if}
