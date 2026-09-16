<script lang="ts">
  // One chat thread, from the flux chat screen: the transcript above an input row pinned
  // to the bottom. The top bar carries the title, back, and the link to saved chats.
  import { afterUpdate, onMount } from 'svelte';
  import ChatMessage from '../ChatMessage.svelte';
  import Icon from '../Icon.svelte';
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
  <div class="thread" bind:this={list}>
    {#if !messages.length}
      <div class="hint">Ask a question about a situation, and the answer quotes the library.</div>
    {/if}
    {#each messages as m (m.id)}
      <ChatMessage message={m} />
    {/each}
  </div>
  <div class="input-area">
    <div class="input-row">
      <input bind:value={draft} placeholder="Ask a question" aria-label="Ask a question" on:keydown={(e) => e.key === 'Enter' && submit()} />
      <button class="send" aria-label="Send" disabled={!draft.trim() || sending} on:click={() => submit()}><Icon name="arrow-up" /></button>
    </div>
  </div>
</div>
