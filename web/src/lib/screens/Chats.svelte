<script lang="ts">
  // Saved chats, newest first; a row reopens its thread (flux chats.tsx).
  import Icon from '../Icon.svelte';
  import { threads } from '../core/chat';
  const day = (iso: string) => new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
</script>

<div class="screen">
  {#if !$threads.length}
    <div class="hint">Nothing yet. Questions asked on the home screen save here.</div>
  {:else}
    <div class="chat-rows">
      {#each $threads as t (t.id)}
        <a class="chat-row" href={`#/chat/${t.id}`}>
          <div>
            <div class="t">{t.title}</div>
            <div class="s">{day(t.startedAt)}, {t.messages.length} messages</div>
          </div>
          <span class="chev"><Icon name="chevron-right" size={16} /></span>
        </a>
      {/each}
    </div>
  {/if}
  <div class="askrow"><a class="chip" href="#/">New chat</a></div>
</div>
