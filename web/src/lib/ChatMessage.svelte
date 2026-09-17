<script lang="ts">
  // One bubble, from flux ChatMessage.tsx: the user's on the right in the signature
  // colour, the library's on the left as a translucent card with a source line (book
  // icon, document and page, opening the page) and a queue line (plus icon) when the
  // question was noted for the library.
  import Icon from './Icon.svelte';
  import type { ChatMessage } from './core/chat';
  export let message: ChatMessage;
  $: pages = (message.sources ?? []).filter((s, i, all) => all.findIndex((x) => x.volume === s.volume && x.page === s.page) === i).slice(0, 3);
</script>

{#if message.role === 'user'}
  <div class="bubble user">{message.text}</div>
{:else}
  <div class="bubble assistant">
    {#if message.pending}
      <span class="dots" aria-label="Thinking"><i></i><i></i><i></i></span>
    {:else}
      <p>{message.text}</p>
      {#each pages as s}
        <a class="line" href={`#/volume/${s.volume}?page=${s.page}&passage=${encodeURIComponent(s.passage)}`}><Icon name="book-open" size={12} />{s.title}, page {s.page}</a>
      {/each}
      {#if message.queued}
        <a class="line" href="#/digest"><Icon name="plus-circle" size={12} />Queued for online retrieval: {message.queued.topic}<Icon name="chevron-right" size={12} /></a>
      {:else if message.stored}
        <a class="line" href="#/digest"><Icon name="clock" size={12} />Queued<Icon name="chevron-right" size={12} /></a>
      {/if}
    {/if}
  </div>
{/if}
