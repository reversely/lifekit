<script lang="ts">
  // Saved chats, newest first; a row reopens its thread (flux chats.tsx).
  import { threads } from '../core/chat';
  const day = (iso: string) => new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
</script>

<div class="screen">
  <div class="top"><h1>Chats</h1></div>
  {#if !$threads.length}
    <div class="hint">Nothing yet. Questions asked in Chat save here.</div>
  {:else}
    <div class="chat-rows">
      {#each $threads as t (t.id)}
        <a class="chat-row" href={`#/chat/${t.id}`}>
          <div>
            <div class="t">{t.title}</div>
            <div class="s">{day(t.startedAt)}, {t.messages.length} messages</div>
          </div>
          <span class="chev">›</span>
        </a>
      {/each}
    </div>
  {/if}
  <div class="syncrow"><a class="res sync" href="#/chat">New chat</a></div>
</div>
