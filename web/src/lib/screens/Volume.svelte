<script lang="ts">
  import type { Database } from '../core/db';
  import { outline, page, pageCount, passagesOf, volume, volumeMeta } from '../core/queries';
  import { SECTIONS } from '../core/types';
  import { candidates as fetchCandidates, verdict as sendVerdict, type Candidate } from '../core/api';
  import { applyVerdict } from '../core/db';
  import { onMount } from 'svelte';
  import Thumb from '../Thumb.svelte';
  export let db: Database;

  let filingSelect: HTMLSelectElement | null = null;

  let candidate: Candidate | null = null;
  let filing: string | null = null;
  let judging = false;
  let note = '';

  async function loadCandidate() {
    candidate = null;
    if (v?.admission !== 'staged') return;
    try {
      candidate = (await fetchCandidates()).candidates.find((c) => c.id === id) ?? null;
      filing = candidate?.section ?? null;
    } catch {
      candidate = null;
    }
  }

  async function judge(kind: 'admit' | 'refile' | 'reject') {
    judging = true;
    note = '';
    try {
      const r = await sendVerdict(id, kind, kind === 'refile' ? filing : null);
      if (r.error) {
        note = r.error;
      } else {
        applyVerdict(db, id, r.admission ?? (kind === 'reject' ? 'rejected' : 'admitted'), kind === 'refile' ? filing : null);
        if (kind === 'reject') location.hash = '#/recent';
        else note = kind === 'refile' ? 'Refiled and admitted.' : 'Admitted.';
        candidate = null;
      }
    } catch (e) {
      note = `Failed: ${String(e)}`;
    }
    judging = false;
  }

  $: id, v, loadCandidate();
  onMount(loadCandidate);

  /** Keys: A admits, R refiles when the select differs, Escape blurs; arrows page. */
  function keys(e: KeyboardEvent) {
    const target = e.target as HTMLElement | null;
    const typing = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA');
    const inSelect = target && target.tagName === 'SELECT';
    if (e.key === 'Escape') {
      target?.blur();
      return;
    }
    if (typing || inSelect) return;
    if (e.key === 'ArrowLeft' && current > 1) current -= 1;
    else if (e.key === 'ArrowRight' && current < total) current += 1;
    else if (v?.admission === 'staged' && !judging && !e.metaKey && !e.ctrlKey && !e.altKey) {
      if (e.key === 'a' || e.key === 'A') judge('admit');
      else if ((e.key === 'r' || e.key === 'R') && filing && filing !== candidate?.section) judge('refile');
    }
  }
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

<svelte:window on:keydown={keys} />

{#if v}
  <div class="screen vol">
    <div class="top">
            <h1 class="vol-title">{v.title}</h1>
      <span class="sub">{v.publisher}, {v.edition}</span>
      {#if v.admission === 'staged'}<span class="tag new block">New download</span>{/if}
    </div>
    <div class="vol-cols">
    <aside class="vol-panel">
    {#if v.admission === 'staged'}
      <div class="group">Waiting for your verdict</div>
      <div class="res packet">
        {#if candidate?.question}
          <div class="src"><b>You asked: {candidate.question.text}</b></div>
          {#if candidate.question.wanted}<div class="src">Looking for: {candidate.question.wanted}</div>{/if}
          {#if candidate.question.answer}<p>{candidate.question.answer}</p>{/if}
        {:else if candidate === null}
          <div class="src">The question that pulled this is not on record.</div>
        {/if}
        <div class="filing">
          <span class="src">Filed under</span>
          <select bind:value={filing} bind:this={filingSelect} aria-label="Filed under">
            {#each SECTIONS as s}<option value={s.id}>{s.title}</option>{/each}
          </select>
        </div>
        <div class="verdicts">
          <button class="chip ask" disabled={judging} on:click={() => judge('admit')} title="A">Admit</button>
          <button class="chip" disabled={judging || !filing || filing === candidate?.section} on:click={() => judge('refile')} title="R">Refile</button>
          <button class="chip" disabled={judging} on:click={() => judge('reject')}>Reject</button>
        </div>
        {#if note}<div class="src">{note}</div>{/if}
      </div>
    {:else if note}
      <div class="hint">{note}</div>
    {/if}
    <div class="vol-head">
      <Thumb id={v.id} title={v.title} publisher={v.publisher} big />
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
    </aside>
    <div class="vol-article">
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
    </div>
  </div>
{:else}
  <div class="screen"><div class="top"><h1>Not in the library</h1></div></div>
{/if}
