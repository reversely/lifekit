<script lang="ts">
  // One chat thread, carried over from the flux chat screen: the transcript, an input
  // row pinned to the bottom, a link to the saved chats.
  import { afterUpdate, onMount } from 'svelte';
  import ChatMessage from '../ChatMessage.svelte';
  import { activeId, open, send, startNew, threads } from '../core/chat';
  import { online } from '../core/net';
  export let id: string | null = null;
  export let ask: string | null = null;

  let draft = '';
  let list: HTMLDivElement;
  let sending = false;

  onMount(() => {
    if (id) open(id);
    else startNew();
    if (ask) submit(ask);
  });
  $: if (id) open(id);
  $: thread = $threads.find((t) => t.id === $activeId) ?? null;
  $: messages = thread?.messages ?? [];
  afterUpdate(() => list?.scrollTo({ top: list.scrollHeight }));

  async function submit(text = draft) {
    const q = text.trim();
    if (!q || sending) return;
    draft = '';
    sending = true;
    await send(q, $online);
    sending = false;
    if ($activeId && location.hash !== `#/chat/${$activeId}`) history.replaceState(null, '', `#/chat/${$activeId}`);
  }
</script>

<div class="screen chat">
  <div class="top chat-top">
    <div>
      <h1>Chat</h1>
      <span class="sub">{$online ? 'Online' : 'Offline'}, answers quote the library</span>
    </div>
    <div class="chat-links">
      <a class="chip" href="#/chats">Chats</a>
      <button class="chip" on:click={() => { startNew(); location.hash = '#/chat'; }}>New</button>
    </div>
  </div>
  <div class="thread" bind:this={list}>
    {#if !messages.length}
      <div class="hint">Ask about a situation: bleeding, shelter, fire, water, food, animals, rope work, finding your way.</div>
    {/if}
    {#each messages as m (m.id)}
      <ChatMessage message={m} />
    {/each}
  </div>
  <div class="input-area">
    <div class="input-row">
      <input bind:value={draft} placeholder="Ask a question" aria-label="Ask a question" on:keydown={(e) => e.key === 'Enter' && submit()} />
      <button class="send" aria-label="Send" disabled={!draft.trim() || sending} on:click={() => submit()}>↑</button>
    </div>
  </div>
</div>
