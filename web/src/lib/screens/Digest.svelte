<script lang="ts">
  import { onMount } from 'svelte';
  import { digest as fetchDigest, flush, queued, sync, type Digest } from '../core/api';
  import { online } from '../core/net';

  let data: Digest | null = null;
  let status = '';
  let working = false;
  $: pending = queued();

  async function load() {
    try {
      data = await fetchDigest();
    } catch {
      data = null;
    }
  }

  async function runSync() {
    working = true;
    status = 'Sending stored questions…';
    try {
      const n = await flush();
      status = n ? `${n} question${n === 1 ? '' : 's'} sent. Finding sources…` : 'Finding sources…';
      const result = await sync();
      status = result.events.join(' · ') || 'Nothing to work.';
      await load();
      dispatchEvent(new CustomEvent('lifekit:reload'));
    } catch (e) {
      status = `Sync failed: ${String(e)}`;
    }
    working = false;
    pending = queued();
  }

  onMount(load);
</script>

<div class="screen">
  <div class="top"><h1>Digest</h1><span class="sub">{$online ? 'Online' : 'Offline'}</span></div>

  {#if pending.length}
    <div class="group">Waiting for the network</div>
    {#each pending as q}
      <div class="res"><p>{q.text}</p><div class="src">stored {q.at.slice(0, 16).replace('T', ' ')}</div></div>
    {/each}
  {/if}

  {#if $online}
    <div class="syncrow">
      <button class="res sync" on:click={runSync} disabled={working}>{working ? 'Working…' : 'Sync now'}</button>
    </div>
    {#if status}<div class="hint">{status}</div>{/if}
  {:else}
    <div class="hint">Questions wait here until the network returns.</div>
  {/if}

  {#if data}
    {#if data.answered.length}
      <div class="group">Answered</div>
      {#each data.answered as a}
        <div class="res">
          <div class="src"><b>You asked: {a.question}</b></div>
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
          <div class="src"><b>{v.title}</b>, {v.publisher}</div>
          <p>{v.line || 'Cover pending.'}</p>
          <a class="open" href={`#/volume/${v.id}`}>Open volume</a>
        </div>
      {/each}
    {/if}
    {#if !data.answered.length && !data.added.length && !pending.length}
      <div class="hint">Nothing new since you were last online.</div>
    {/if}
  {/if}
</div>
