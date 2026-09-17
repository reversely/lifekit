<script lang="ts">
  import { onMount } from 'svelte';
  import { config as fetchConfig, digest as fetchDigest, flush, queued, syncStream, verdict as sendVerdict, type Config, type Digest, type LoopEvent } from '../core/api';
  import { applyVerdict } from '../core/db';
  import { sectionTitle } from '../core/sections';
  import LoopTrail from '../LoopTrail.svelte';
  import { online } from '../core/net';
  import NetToggle from '../NetToggle.svelte';
  import type { Database } from '../core/db';
  export let db: Database | null = null;

  let data: Digest | null = null;
  let cfg: Config | null = null;
  let status = '';
  let events: LoopEvent[] = [];
  let working = false;
  $: pending = queued();

  async function load() {
    try {
      data = await fetchDigest();
    } catch {
      data = null;
    }
    try {
      cfg = await fetchConfig();
    } catch {
      cfg = null;
    }
  }

  async function runSync() {
    working = true;
    status = '';
    events = [];
    try {
      const n = await flush();
      status = n ? `${n} question${n === 1 ? '' : 's'} sent.` : '';
      const last = await syncStream((e) => (events = [...events, e]));
      if (last?.note) status = last.note;
      else if (!events.some((e) => !e.done)) status = 'Nothing to work.';
      await load();
      dispatchEvent(new CustomEvent('lifekit:reload'));
    } catch (e) {
      status = `Send failed: ${String(e)}`;
    }
    working = false;
    pending = queued();
  }

  const reasonOf = (origin: string) => (origin.startsWith('rule:') ? 'From the profile' : 'Asked');
  const twoSentences = (text: string) => (text || 'No cover yet.').replace(/\n/g, ' ').split(/(?<=[.!?])\s+/).slice(0, 2).join(' ');
  let added: Record<string, boolean> = {};
  async function act(id: string, kind: 'admit' | 'reject') {
    try {
      const r = await sendVerdict(id, kind, null);
      if (r.error) return;
      if (db) applyVerdict(db, id, r.admission ?? (kind === 'reject' ? 'rejected' : 'admitted'), null);
      if (kind === 'admit') added = { ...added, [id]: true };
      else if (data) data = { ...data, candidates: data.candidates.filter((c) => c.id !== id) };
    } catch {
      /* the row stays */
    }
  }

  onMount(load);
</script>

<div class="screen">
  <div class="top">
    <h1>Digest</h1>
    <span class="sub"><NetToggle size={14} />{cfg ? `${cfg.small}${cfg.loop ? '' : ', downloads off'}` : ''}</span>
  </div>

  {#if pending.length}
    <div class="group">Waiting for the network</div>
    {#each pending as q}
      <div class="res"><p>{q.text}</p><div class="src">Stored {q.at.slice(0, 16).replace('T', ' ')}</div></div>
    {/each}
  {/if}

  {#if $online}
    <div class="syncrow">
      <button class="res sync" on:click={runSync} disabled={working}>{working ? 'Working' : 'Send stored questions'}</button>
    </div>
    {#if status}<div class="hint">{status}</div>{/if}
    {#if events.length || working}<div class="group">Search steps</div><LoopTrail {db} {events} {working} />{/if}
  {:else}
    <div class="hint">Stored questions are sent when the network returns.</div>
  {/if}

  {#if data}
    {#if data.candidates.length}
      <div class="group">New downloads</div>
      <div class="hint">Downloaded since the last digest.</div>
      {#each data.candidates as c (c.id)}
        <div class="res">
          <div class="src"><b>{c.title}</b>, {c.publisher}{#if c.section}, {db ? sectionTitle(db, c.section) : c.section}{/if}</div>
          <p>{twoSentences(c.cover)}</p>
          {#if added[c.id]}
            <div class="src">Added.</div>
          {:else}
            <div class="verdicts">
              <button class="chip ask" on:click={() => act(c.id, 'admit')}>Add to library</button>
              <button class="chip" on:click={() => act(c.id, 'reject')}>Remove</button>
              <a class="open" href={`#/volume/${c.id}`}>Open</a>
            </div>
          {/if}
        </div>
      {/each}
    {/if}
    {#if data.pending.length}
      <div class="group">Questions in progress</div>
      {#each data.pending as q}
        <div class="res">
          <p>{q.text}</p>
          <div class="src">{reasonOf(q.origin)}{q.topic ? `, ${q.topic}` : ''}</div>
        </div>
      {/each}
    {/if}
    {#if data.answered.length}
      <div class="group">Answered</div>
      {#each data.answered as a}
        <div class="res">
          <div class="src"><b>Question: {a.question}</b></div>
          <p>{a.answer}</p>
          <div class="src">{a.state}, {a.at.slice(0, 16).replace('T', ' ')}{a.volumes.length ? `, from ${a.volumes.join(', ')}` : ''}</div>
          {#each a.volumes as v}<a class="open" href={`#/volume/${v}`}>Open volume</a>{/each}
        </div>
      {/each}
    {/if}
    {#if data.added.length}
      <div class="group">Added to the library</div>
      {#each data.added as v}
        <div class="res">
          <div class="src"><b>{v.title}</b>, {v.publisher}{#if v.admission === 'staged'}<span class="tag new">New download</span>{/if}</div>
          <p>{v.line || 'No cover yet.'}</p>
          <a class="open" href={`#/volume/${v.id}`}>Open volume</a>
        </div>
      {/each}
    {/if}
    {#if !data.answered.length && !data.added.length && !pending.length && !data.candidates.length && !data.pending.length}
      <div class="hint">Nothing new.</div>
    {/if}
  {/if}
  <div class="askrow"><a class="chip" href="#/profile">Profile</a></div>
</div>
