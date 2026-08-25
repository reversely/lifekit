<script lang="ts">
  import { onMount } from 'svelte';
  import type { Database } from './lib/core/db';
  import { database } from './lib/core/db';
  import Library from './lib/screens/Library.svelte';
  import Recent from './lib/screens/Recent.svelte';
  import Section from './lib/screens/Section.svelte';
  import Search from './lib/screens/Search.svelte';
  import Volume from './lib/screens/Volume.svelte';
  import Digest from './lib/screens/Digest.svelte';
  import { online } from './lib/core/net';
  import { queued } from './lib/core/api';

  let db: Database | null = null;
  let route = location.hash.replace(/^#/, '') || '/';

  onMount(async () => {
    db = await database();
    addEventListener('hashchange', () => (route = location.hash.replace(/^#/, '') || '/'));
  });

  $: parts = route.split('?')[0].split('/').filter(Boolean);
  $: params = new URLSearchParams(route.split('?')[1] ?? '');
  $: screen = parts[0] ?? '';
</script>

{#if !db}
  <div class="screen"><div class="top"><h1>Library</h1><span class="sub">Opening…</span></div></div>
{:else if screen === 'recent'}
  <Recent {db} />
{:else if screen === 'section'}
  <Section {db} id={parts[1]} />
{:else if screen === 'search'}
  <Search {db} initial={params.get('q') ?? ''} />
{:else if screen === 'digest'}
  <Digest />
{:else if screen === 'volume'}
  <Volume {db} id={parts[1]} initialPage={Number(params.get('page') ?? 1)} highlight={params.get('passage')} />
{:else}
  <Library {db} />
{/if}

<nav class="nav" class:paper={screen === ''}>
  <a href="#/" class:on={screen === ''}>Library</a>
  <a href="#/recent" class:on={screen === 'recent'}>Recent</a>
  <a href="#/search" class:on={screen === 'search'}>Search</a>
  <a href="#/digest" class:on={screen === 'digest'}>Digest{#if queued().length}<span class="dot"></span>{/if}</a>
  <span class="net" class:off={!$online} title={$online ? 'Online' : 'Offline'}></span>
</nav>
