<script lang="ts">
  // The chat home from flux app/index.tsx: the wordmark, the tagline, three questions
  // from the gallery rotating on a timer, and the ask row pinned at the bottom. A send
  // starts a new thread and lands in it.
  import { onDestroy, onMount } from 'svelte';
  import { get } from 'svelte/store';
  import Icon from '../Icon.svelte';
  import { activeId, send, startNew } from '../core/chat';
  import { online } from '../core/net';

  // One question per subject the library answers; tapping one sends it as-is.
  const GALLERY_QUESTIONS = [
    'How do I purify water?',
    'Which way is north without a compass?',
    'How do I keep a fire going in rain?',
    'How do I treat a blister on trail?',
    'Something bit me. What now?',
    'How do I signal a plane?',
    'How much bleach for a gallon of water?',
    'How do I stop heavy bleeding?',
    'What do I do if I get lost on a hike?',
  ];
  const VISIBLE = 3;
  const ROTATE_MS = 5000;
  const FADE_MS = 350;

  let start = 0;
  let faded = false;
  let timer: ReturnType<typeof setInterval>;
  $: visible = Array.from({ length: VISIBLE }, (_, i) => GALLERY_QUESTIONS[(start + i) % GALLERY_QUESTIONS.length]);

  onMount(() => {
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    timer = setInterval(() => {
      if (reduce) {
        start = (start + VISIBLE) % GALLERY_QUESTIONS.length;
        return;
      }
      faded = true;
      setTimeout(() => {
        start = (start + VISIBLE) % GALLERY_QUESTIONS.length;
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
    <a class="source-row" href="#/library">Answers quote the library.</a>
  </div>
</div>
