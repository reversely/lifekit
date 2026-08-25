<script lang="ts">
  import type { Database } from '../core/db';
  import Chips from '../Chips.svelte';
  import { matchingVolumes, search, tagCounts } from '../core/queries';
  import { answer as askApi, enqueue, type AnswerResult } from '../core/api';
  import { online } from '../core/net';
  export let db: Database;
  export let initial = '';

  let query = initial;
  let lastInitial = initial;
  $: if (initial !== lastInitial) {
    lastInitial = initial;
    query = initial;
    reply = null;
    stored = null;
  }
  let active: string | null = null;
  let asking = false;
  let reply: AnswerResult | null = null;
  let stored: string | null = null;

  async function ask() {
    const q = query.trim();
    if (!q) return;
    reply = null;
    stored = null;
    if (!$online) {
      enqueue(q);
      stored = 'offline';
      return;
    }
    asking = true;
    try {
      reply = await askApi(q, active);
      if (!reply.answered) stored = reply.stored ?? 'server';
    } catch {
      enqueue(q);
      stored = 'offline';
    }
    asking = false;
  }
  const counts = tagCounts(db);
  $: hits = query.trim() ? search(db, query, { tag: active ?? undefined }) : [];
  $: vols = query.trim() ? matchingVolumes(db, query) : [];

  const short = (text: string) => (text || '').replace(/\n/g, ' ').split(/(?<=[.!?])\s+/).slice(0, 2).join(' ');
</script>

<div class="screen">
  <div class="top"><h1>Search</h1></div>
  <div class="bar">
    <input bind:value={query} placeholder="Ask the library" on:keydown={(e) => e.key === 'Enter' && ask()} />
    {#if query}<button class="x" on:click={() => ((query = ''), (reply = null), (stored = null))}>×</button>{/if}
  </div>
  <div class="askrow">
    <button class="chip ask" on:click={ask} disabled={asking || !query.trim()}>{asking ? 'Asking…' : 'Ask'}</button>
    <span class="hint inline">{$online ? 'Online: the model answers from the pages below.' : 'Offline: a question is stored until the network returns.'}</span>
  </div>
  {#if reply?.answered}
    <div class="group">Answer</div>
    <div class="res answer">
      <p>{reply.answer}</p>
      {#each reply.hits.slice(0, 2) as h}
        <div class="src" style="margin-top:8px"><b>{h.title}</b>, {h.edition}, page {h.page}</div>
        <a class="open" href={`#/volume/${h.volume}?page=${h.page}&passage=${encodeURIComponent(h.passage)}`}>Open page {h.page}</a>
      {/each}
    </div>
  {:else if stored}
    <div class="group">Stored</div>
    <div class="res"><p>{stored === 'offline' ? 'You are offline. This question is stored and will be worked when the network returns.' : 'Nothing in the library answers this yet. Stored; a source will be found when the loop next runs.'}</p><a class="open" href="#/digest">Open the digest</a></div>
  {/if}
  <Chips {counts} {active} onFilter={(t) => (active = t)} />
  {#if vols.length}
    <div class="group">Volumes</div>
    {#each vols as v}
      <div class="res">
        <div class="src"><b>{v.title}</b>, {v.edition}</div>
        <p>{short(v.cover)}</p>
        <a class="open" href={`#/volume/${v.id}`}>Open volume</a>
      </div>
    {/each}
  {/if}
  {#if query.trim()}
    <div class="group">In the pages</div>
    {#each hits as h}
      <div class="res">
        <div class="src"><b>{h.title}</b>, {h.edition}, page {h.page}</div>
        <p>{h.text.length > 360 ? h.text.slice(0, 360) + '…' : h.text}</p>
        <a class="open" href={`#/volume/${h.volume}?page=${h.page}&passage=${encodeURIComponent(h.passage)}`}>Open page {h.page}</a>
      </div>
    {/each}
    {#if !hits.length}
      <div class="hint">Nothing in the library answers this. Stored for when you are online.</div>
    {/if}
  {/if}
</div>
