<script lang="ts">
  // The demo route: five stations, each running the model or the loop for real, with one
  // paragraph stating what happens and why (docs/content/deployments-and-approval.md 4).
  import { onDestroy, onMount } from 'svelte';
  import type { Database } from '../core/db';
  import { reload } from '../core/db';
  import { answer as askApi, candidates as fetchCandidates, config as fetchConfig, enqueue, flush, queued, syncStream, type AnswerResult, type Candidate, type LoopEvent } from '../core/api';
  import { forceOffline, online } from '../core/net';
  import LoopTrail from '../LoopTrail.svelte';
  import Volume from './Volume.svelte';
  import Section from './Section.svelte';
  export let db: Database;
  export let step = 1;

  let model = '';
  onMount(async () => {
    try {
      model = (await fetchConfig()).small;
    } catch {
      model = '';
    }
  });

  // station 1: ask the model
  let q1 = 'how much bleach for a gallon of water';
  let reply: AnswerResult | null = null;
  let asking = false;
  async function ask1() {
    asking = true;
    reply = null;
    try {
      reply = await askApi(q1);
    } catch (e) {
      reply = { answered: false, hits: [], stored: undefined } as AnswerResult;
    }
    asking = false;
  }

  // station 2: store while offline
  let q2 = 'how to splint a broken wrist with a magazine';
  let stored = false;
  function ask2() {
    enqueue(q2);
    stored = true;
  }

  // station 3: the loop, streamed
  let events: LoopEvent[] = [];
  let working = false;
  let ran = false;
  let sent = 0;
  async function runLoop() {
    working = true;
    events = [];
    try {
      sent = await flush();
      await syncStream((e) => (events = [...events, e]));
      await reload();
      dispatchEvent(new CustomEvent('lifekit:reload'));
    } catch (e) {
      events = [...events, { question: '', step: 'search_failed', at: '', source: String(e) }];
    }
    working = false;
    ran = true;
  }

  // station 4: the document the stored question pulled
  let candidate: Candidate | null = null;
  async function findCandidate() {
    try {
      const all = (await fetchCandidates()).candidates;
      candidate = all.find((c) => c.question && c.question.text === q2) ?? all.find((c) => c.question) ?? all[0] ?? null;
    } catch {
      candidate = null;
    }
  }

  const stations = [
    { title: 'Ask the library', text: 'The model answers from the pages on this device and quotes the page it used. Change the question if you like, then press Ask.' },
    { title: 'Ask without a network', text: 'This station switches the app to offline. Press Ask: the question waits in this browser until the network returns.' },
    { title: 'The loop works the question', text: 'Back online, the stored question goes to the loop. Watch each step: the model names a topic, the offline Wikipedia on this device is searched, the model picks the articles that fit, files them into a binder, and the question is asked again.' },
    { title: 'Your verdict', text: 'Every document the loop adds waits for the owner. The packet shows the question that pulled it, the answer it gives, and the filing. Admit keeps it, Refile moves it, Reject removes it and the loop never pulls it again.' },
    { title: 'In its binder', text: 'An admitted document sits in its binder like any other volume, with its cover, licence, and page count. The New download marker is gone.' },
  ];
  $: current = stations[step - 1] ?? stations[0];

  // entering a station: switch offline for 2, run the loop for 3, find the candidate for 4
  let lastStep = 0;
  $: if (step !== lastStep) {
    lastStep = step;
    forceOffline.set(step === 2);
    if (step === 1 && !reply && !asking) ask1();
    if (step === 3 && !ran && !working) runLoop();
    if (step >= 4) findCandidate();
  }
  onDestroy(() => forceOffline.set(false));
  const go = (n: number) => (location.hash = `#/demo/${Math.min(5, Math.max(1, n))}`);
  $: section = candidate?.section ?? 'medicine';
</script>

<div class="demo">
  <div class="station">
    <div class="screen">
      <div class="station-head">
        <span class="lab">How it works, {step} of 5{#if model}, {model}{/if}</span>
        <h2>{current.title}</h2>
        <p>{current.text}</p>
        <div class="station-nav">
          <button class="chip" disabled={step <= 1} on:click={() => go(step - 1)}>Back</button>
          {#if step < 5}
            <button class="chip ask" on:click={() => go(step + 1)}>Next</button>
          {:else}
            <a class="chip ask" href="#/">Open the library</a>
          {/if}
        </div>
      </div>
    </div>
  </div>

  <div class="screen">
    {#if step === 1}
      <div class="top"><h1>Search</h1><span class="sub">{$online ? 'Online' : 'Offline'}</span></div>
      <div class="bar"><input bind:value={q1} aria-label="Question" on:keydown={(e) => e.key === 'Enter' && ask1()} /></div>
      <div class="askrow"><button class="chip ask" on:click={ask1} disabled={asking}>{asking ? 'Asking…' : 'Ask'}</button><span class="hint inline">The model reads the top passages and answers with a quote.</span></div>
      {#if reply?.answered}
        <div class="group">Answer</div>
        <div class="res answer">
          <p>{reply.answer}</p>
          {#each reply.hits.slice(0, 2) as h}
            <div class="src" style="margin-top:8px"><b>{h.title}</b>, {h.edition}, page {h.page}</div>
            <a class="open" href={`#/volume/${h.volume}?page=${h.page}&passage=${encodeURIComponent(h.passage)}`}>Open page {h.page}</a>
          {/each}
        </div>
      {:else if reply}
        <div class="group">Stored</div>
        <div class="res"><p>Nothing in the library answers this. The model wrote down what is missing{reply.wanted ? `: ${reply.wanted}` : ''}. Stored for the loop.</p></div>
      {/if}
    {:else if step === 2}
      <div class="top"><h1>Search</h1><span class="sub">{$online ? 'Online' : 'Offline'}</span></div>
      <div class="bar"><input bind:value={q2} aria-label="Question" on:keydown={(e) => e.key === 'Enter' && ask2()} /></div>
      <div class="askrow"><button class="chip ask" on:click={ask2}>Ask</button><span class="hint inline">Offline: a question is stored until the network returns.</span></div>
      {#if stored || queued().some((x) => x.text === q2)}
        <div class="group">Stored</div>
        <div class="res"><p>You are offline. This question is stored in this browser and will be worked on the next station.</p></div>
      {/if}
    {:else if step === 3}
      <div class="top"><h1>Digest</h1><span class="sub">{$online ? 'Online' : 'Offline'}{#if sent}, {sent} sent{/if}</span></div>
      {#if !working && ran}
        <div class="syncrow"><button class="res sync" on:click={runLoop}>Run the loop again</button></div>
      {/if}
      <div class="group">The loop, step by step</div>
      <LoopTrail {events} {working} />
      {#if !working && ran && !events.some((e) => !e.done)}<div class="hint">Nothing was waiting. Go back to station 2, press Ask, then return.</div>{/if}
    {:else if step === 4}
      {#if candidate}
        <Volume {db} id={candidate.id} />
      {:else}
        <div class="top"><h1>Your verdict</h1></div>
        <div class="hint">Nothing waits for a verdict right now. Run the loop on the previous station, then come back.</div>
      {/if}
    {:else}
      <Section {db} id={section} />
    {/if}
  </div>
</div>
