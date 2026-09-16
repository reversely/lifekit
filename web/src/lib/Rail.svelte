<script lang="ts">
  // The desktop side rail: the four screens, the twelve sections with counts, the profile
  // line, and the network switch. Hidden below 900 px, where the bottom nav serves.
  import { onMount } from 'svelte';
  import type { Database } from './core/db';
  import { shelves } from './core/queries';
  import { config as fetchConfig, profile as fetchProfile } from './core/api';
  import { forceOffline, online } from './core/net';
  export let db: Database;
  export let screen: string;
  export let sectionId: string | null = null;

  $: list = shelves(db);
  let summary: string | null = null;
  let model = '';

  async function load() {
    try {
      const p = await fetchProfile();
      summary = p.profile.updated_at ? p.summary || 'Set up' : '';
    } catch {
      summary = null;
    }
    try {
      model = (await fetchConfig()).small;
    } catch {
      model = '';
    }
  }
  onMount(() => {
    load();
    addEventListener('lifekit:reload', load);
    return () => removeEventListener('lifekit:reload', load);
  });
</script>

<aside class="rail" aria-label="Sections and screens">
  <a class="brand" href="#/">LifeKit</a>
  <nav class="screens">
    <a href="#/chat" class:on={screen === 'chat' || screen === 'chats'}>Chat</a>
    <a href="#/" class:on={screen === ''}>Library</a>
    <a href="#/recent" class:on={screen === 'recent'}>Recent</a>
    <a href="#/search" class:on={screen === 'search'}>Search</a>
    <a href="#/digest" class:on={screen === 'digest'}>Digest</a>
    <a href="#/demo/1" class:on={screen === 'demo'}>How it works</a>
  </nav>
  <div class="lab">Sections</div>
  <nav class="sections">
    {#each list as s}
      <a href={`#/section/${s.id}`} class:on={screen === 'section' && sectionId === s.id} class:empty={!s.count}>
        <span class="n">{s.order}</span><span class="t">{s.title}</span><span class="c">{s.count || ''}</span>
      </a>
    {/each}
  </nav>
  <div class="foot">
    {#if summary !== null}
      <a class="profile" href="#/profile" class:on={screen === 'profile'}>
        <span class="t">{summary ? 'Profile' : 'Set up your profile'}</span>
        {#if summary}<span class="s">{summary}</span>{/if}
      </a>
    {/if}
    <button class="net" class:off={!$online} on:click={() => forceOffline.update((v) => !v)} title={$forceOffline ? 'Back online' : 'Simulate offline'}>
      <span class="dot"></span>{$online ? 'Online' : 'Offline'}
    </button>
    {#if model}<div class="model">{model}</div>{/if}
  </div>
</aside>
