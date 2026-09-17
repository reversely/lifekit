<script lang="ts">
  // The modal on the offline-to-online transition. When the online store goes from false to
  // true, the modal measures the connection, sends the stored questions, and runs the online retrieval
  // with the trail in view. First load never opens the modal.
  import { onMount } from 'svelte';
  import type { Database } from './core/db';
  import { reload } from './core/db';
  import { config as fetchConfig, flush, queued, syncStream, type RetrievalEvent } from './core/api';
  import { online } from './core/net';
  import RetrievalSteps from './RetrievalSteps.svelte';
  export let db: Database | null = null;

  const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';

  let open = false;
  let was: boolean | null = null;
  let rtt: number | null = null;
  let bars = 0;
  let netLine = '';
  let stored: { text: string; at: string }[] = [];
  let sendState: 'idle' | 'sending' | 'sent' = 'idle';
  let retrievalState: 'idle' | 'running' | 'done' | 'off' | 'nothing' = 'idle';
  let events: RetrievalEvent[] = [];
  let closeButton: HTMLButtonElement | null = null;

  async function measure() {
    const times: number[] = [];
    for (let i = 0; i < 3; i++) {
      const t0 = performance.now();
      try {
        await fetch(`${BASE}/api/health`, { cache: 'no-store' });
        times.push(performance.now() - t0);
      } catch {
        /* a failed probe adds no sample */
      }
    }
    times.sort((a, b) => a - b);
    rtt = times.length ? Math.round(times[Math.floor(times.length / 2)]) : null;
    bars = rtt === null ? 0 : rtt < 100 ? 4 : rtt < 300 ? 3 : rtt < 1000 ? 2 : 1;
    const conn = (navigator as any).connection as { effectiveType?: string; downlink?: number } | undefined;
    const parts = [];
    if (rtt !== null) parts.push(`Round trip ${rtt} ms`);
    if (conn?.effectiveType) parts.push(conn.effectiveType);
    if (conn?.downlink) parts.push(`${conn.downlink} Mbps`);
    netLine = parts.length ? parts.join(', ') + '.' : 'The library on this box did not answer the probe.';
  }

  async function run() {
    open = true;
    events = [];
    sendState = 'idle';
    retrievalState = 'idle';
    stored = queued();
    await measure();
    if (stored.length) {
      sendState = 'sending';
      try {
        await flush();
      } catch {
        /* the digest keeps the queue */
      }
      sendState = 'sent';
    }
    let retrievalOn = true;
    try {
      retrievalOn = (await fetchConfig()).online_retrieval;
    } catch {
      retrievalOn = true;
    }
    if (!retrievalOn) {
      retrievalState = 'off';
      return;
    }
    retrievalState = 'running';
    try {
      await syncStream((e) => (events = [...events, e]));
      await reload();
      dispatchEvent(new CustomEvent('lifekit:reload'));
    } catch {
      /* the trail shows what arrived */
    }
    retrievalState = events.some((e) => !e.done) ? 'done' : 'nothing';
  }

  onMount(() => {
    const stop = online.subscribe((now) => {
      if (was === false && now) void run();
      was = now;
    });
    return stop;
  });

  const close = () => (open = false);
  const keys = (e: KeyboardEvent) => {
    if (open && e.key === 'Escape') close();
  };
  $: if (open) queueMicrotask(() => closeButton?.focus());
</script>

<svelte:window on:keydown={keys} />

{#if open}
  <div class="modal-back" role="presentation" on:click={close} on:keydown={keys}>
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="back-online-title" tabindex="-1" on:click|stopPropagation on:keydown={keys}>
      <div class="modal-head">
        <h2 id="back-online-title">Back online</h2>
        <button class="chip" bind:this={closeButton} on:click={close}>Close</button>
      </div>
      <div class="conn">
        <span class="bars" aria-label={`${bars} of 4 bars`}>
          {#each [1, 2, 3, 4] as n}<i class:on={n <= bars} style={`height:${4 + n * 3}px`}></i>{/each}
        </span>
        <span class="line">{netLine}</span>
      </div>
      {#if stored.length}
        <h3>Queue</h3>
        {#each stored as q}<p class="q">{q.text}</p>{/each}
        <p class="state">{sendState === 'sending' ? `Sending ${stored.length} question${stored.length === 1 ? '' : 's'}.` : sendState === 'sent' ? 'Sent.' : ''}</p>
      {/if}
      <h3>Online retrieval</h3>
      {#if retrievalState === 'off'}
        <p class="state">Online retrieval is off.</p>
      {:else if retrievalState === 'nothing'}
        <p class="state">Nothing to work.</p>
      {:else}
        <RetrievalSteps {db} {events} working={retrievalState === 'running'} />
        {#if retrievalState === 'done'}<p class="state">Done. <a class="inline" href="#/digest" on:click={close}>Open digest</a></p>{/if}
      {/if}
    </div>
  </div>
{/if}
