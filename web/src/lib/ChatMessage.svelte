<script lang="ts">
  // One bubble, carried over from the flux ChatMessage: the user's on the right, the
  // library's on the left with a source line (document and page, opening the page) and
  // a queue line when the question was noted for the library.
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
      {#if pages.length}
        <div class="lines">
          {#each pages as s}
            <a class="line" href={`#/volume/${s.volume}?page=${s.page}&passage=${encodeURIComponent(s.passage)}`}>{s.title}, page {s.page}</a>
          {/each}
        </div>
      {/if}
      {#if message.queued}
        <a class="line" href="#/digest">Noted for the library: {message.queued.topic}</a>
      {:else if message.stored}
        <a class="line" href="#/digest">Stored for the loop</a>
      {/if}
    {/if}
  </div>
{/if}
