<script lang="ts">
  // The chat home from flux app/index.tsx: the wordmark, the tagline, three questions
  // from the gallery rotating on a timer, and the ask row pinned at the bottom. A send
  // starts a new thread and lands in it.
  import { onDestroy, onMount } from 'svelte';
  import { get } from 'svelte/store';
  import Icon from '../Icon.svelte';
  import { activeId, send, startNew } from '../core/chat';
  import { config as fetchConfig } from '../core/api';
  import { online } from '../core/net';

  // The gallery comes from packs/questions.tsv through the API; none while loading.
  let gallery: string[] = [];
  const VISIBLE = 3;
  const ROTATE_MS = 5000;
  const FADE_MS = 350;

  let start = 0;
  let faded = false;
  let timer: ReturnType<typeof setInterval>;
  $: visible = gallery.length ? Array.from({ length: Math.min(VISIBLE, gallery.length) }, (_, i) => gallery[(start + i) % gallery.length]) : [];

  onMount(async () => {
    try {
      gallery = (await fetchConfig()).questions?.gallery ?? [];
    } catch {
      gallery = [];
    }
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    timer = setInterval(() => {
      if (reduce) {
        start = gallery.length ? (start + VISIBLE) % gallery.length : 0;
        return;
      }
      faded = true;
      setTimeout(() => {
        start = gallery.length ? (start + VISIBLE) % gallery.length : 0;
        faded = false;
      }, FADE_MS);
    }, ROTATE_MS);
  });
  onDestroy(() => clearInterval(timer));

  let draft = '';
  function ask(question: string) {
    const q = question.trim();
    if (!q) return;
    draft = '';
    startNew();
    void send(q, get(online));
    location.hash = `#/chat/${get(activeId)}`;
  }
</script>

<div class="home">
  <div class="hero-area">
    <div class="hero">
      <div class="wordmark">LifeKit</div>
      <div class="tagline">A field guide you can ask.</div>
    </div>
    <div class="gallery" class:faded>
      {#each visible as question (question)}
        <button class="pill" on:click={() => ask(question)} aria-label={`Ask: ${question}`}>{question}</button>
      {/each}
    </div>
  </div>
  <div class="ask-area">
    <div class="ask-row">
      <input bind:value={draft} placeholder="Ask a question" aria-label="Ask a question" on:keydown={(e) => e.key === 'Enter' && ask(draft)} />
      <button class="send" aria-label="Send" disabled={!draft.trim()} on:click={() => ask(draft)}><Icon name="arrow-up" /></button>
    </div>
  </div>
</div>
