<script lang="ts">
  // The demo route: five stations, each running the model or the online retrieval for real, with one
  // paragraph stating what happens and why (docs/content/deployments-and-approval.md 4).
  import { onMount } from 'svelte';
  import type { Database } from '../core/db';
  import { reload } from '../core/db';
  import { answer as askApi, candidates as fetchCandidates, config as fetchConfig, enqueue, flush, queued, syncStream, type AnswerResult, type Candidate, type RetrievalEvent } from '../core/api';
  import { online } from '../core/net';
  import { sections } from '../core/sections';
  import RetrievalSteps from '../RetrievalSteps.svelte';
  import NetToggle from '../NetToggle.svelte';
  import Volume from './Volume.svelte';
  import Section from './Section.svelte';
  export let db: Database;
  export let step = 1;

  let model = '';
  let loaded = false;
  onMount(async () => {
    try {
      const c = await fetchConfig();
      model = c.small;
      q1 = c.questions?.demo_answered?.[0] ?? '';
      q2 = c.questions?.demo_stored?.[0] ?? '';
    } catch {
      model = '';
    }
    loaded = true;
    enter(step);
  });

  // station 1: ask the model
  let q1 = '';
  let reply: AnswerResult | null = null;
  let asking = false;
  async function ask1() {
    if (!q1.trim()) return;
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
  let q2 = '';
  let stored = false;
  function ask2() {
    if (!q2.trim()) return;
    enqueue(q2);
    stored = true;
  }

  // station 3: the online retrieval, streamed
  let events: RetrievalEvent[] = [];
  let working = false;
  let ran = false;
  let sent = 0;
  async function runRetrieval() {
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
    { title: 'Ask', text: 'Answers quote a page on this device. Edit the question, press Ask.' },
    { title: 'Ask offline', text: 'Switch offline with the toggle, then press Ask. The browser stores the question until the network returns.' },
    { title: 'Online retrieval', text: 'Each stored question: topic, offline Wikipedia search, article choice, section, download, answer.' },
    { title: 'Curation', text: 'A new download shows its description and its section. Add it to the library, or remove it. A removed document is not pulled again.' },
    { title: 'The binder', text: 'An admitted document lists in the binder as a volume, with cover, licence, and page count, and the New download marker is removed.' },
  ];
  $: current = stations[step - 1] ?? stations[0];

  // entering a station: switch offline for 2, run the online retrieval for 3, find the candidate for 4
  let lastStep = 0;
  function enter(n: number) {
    if (!loaded) return;
    if (n === 1 && !reply && !asking) ask1();
    if (n === 3 && !ran && !working) runRetrieval();
    if (n >= 4) findCandidate();
  }
  $: if (step !== lastStep) {
    lastStep = step;
    enter(step);
  }
  const go = (n: number) => (location.hash = `#/demo/${Math.min(5, Math.max(1, n))}`);
  $: section = candidate?.section ?? sections(db)[0]?.id ?? '';
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
            <a class="chip ask" href="#/library">Open the library</a>
          {/if}
        </div>
      </div>
    </div>
  </div>

  <div class="screen">
    {#if step === 1}
      <div class="top"><h1>Search</h1><span class="sub"><NetToggle size={14} /></span></div>
      <div class="bar"><input bind:value={q1} aria-label="Question" on:keydown={(e) => e.key === 'Enter' && ask1()} /></div>
      <div class="askrow"><button class="chip ask" on:click={ask1} disabled={asking}>{asking ? 'Asking' : 'Ask'}</button><span class="hint inline">The model reads the top passages and answers with a quote.</span></div>
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
        <div class="res"><p>No page answers this. Missing{reply.wanted ? `: ${reply.wanted}` : ''}. Stored.</p></div>
      {/if}
    {:else if step === 2}
      <div class="top"><h1>Search</h1><span class="sub"><NetToggle size={14} /></span></div>
      <div class="bar"><input bind:value={q2} aria-label="Question" on:keydown={(e) => e.key === 'Enter' && ask2()} /></div>
      <div class="askrow"><button class="chip ask" on:click={ask2}>Ask</button><span class="hint inline">The app is offline, so the browser stores the question until the network returns.</span></div>
      {#if stored || queued().some((x) => x.text === q2)}
        <div class="group">Stored</div>
        <div class="res"><p>Offline. Queued; step 3 retrieves for this question.</p></div>
      {/if}
    {:else if step === 3}
      <div class="top"><h1>Digest</h1><span class="sub"><NetToggle size={14} />{#if sent}{sent} sent{/if}</span></div>
      {#if !working && ran}
        <div class="syncrow"><button class="res sync" on:click={runRetrieval}>Run online retrieval</button></div>
      {/if}
      <div class="group">Online retrieval</div>
      <RetrievalSteps {db} {events} {working} />
      {#if !working && ran && !events.some((e) => !e.done)}<div class="hint">No stored question. Return to step 2 and press Ask.</div>{/if}
    {:else if step === 4}
      {#if candidate}
        <Volume {db} id={candidate.id} />
      {:else}
        <div class="top"><h1>New download</h1></div>
        <div class="hint">No new download. Run online retrieval on step 3.</div>
      {/if}
    {:else}
      <Section {db} id={section} />
    {/if}
  </div>
</div>
