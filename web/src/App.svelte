<script lang="ts">
  import { onMount } from 'svelte';
  import type { Database } from './lib/core/db';
  import { database, reload } from './lib/core/db';
  import Welcome from './lib/screens/Welcome.svelte';
  import Profile from './lib/screens/Profile.svelte';
  import { profile as fetchProfile } from './lib/core/api';
  import Library from './lib/screens/Library.svelte';
  import Recent from './lib/screens/Recent.svelte';
  import Section from './lib/screens/Section.svelte';
  import Search from './lib/screens/Search.svelte';
  import Volume from './lib/screens/Volume.svelte';
  import Digest from './lib/screens/Digest.svelte';
  import Demo from './lib/screens/Demo.svelte';
  import Rail from './lib/Rail.svelte';
  import { forceOffline, online } from './lib/core/net';
  import { queued } from './lib/core/api';

  let db: Database | null = null;
  let route = location.hash.replace(/^#/, '') || '/';

  onMount(async () => {
    db = await database();
    addEventListener('hashchange', () => (route = location.hash.replace(/^#/, '') || '/'));
    addEventListener('lifekit:reload', async () => (db = await reload()));
    addEventListener('lifekit:changed', () => (db = db)); // same copy, changed in place
    // first start: the profile is unset and nobody has skipped the welcome
    let dismissed = false;
    try {
      dismissed = localStorage.getItem('lifekit.welcomeDone') === '1';
    } catch {
      dismissed = true;
    }
    if (!dismissed && (route === '/' || route === '')) {
      try {
        const p = await fetchProfile();
        if (!p.profile.updated_at) location.hash = '#/welcome';
      } catch {
        /* no API: stay on the library */
      }
    }
  });

  $: parts = route.split('?')[0].split('/').filter(Boolean);
  $: params = new URLSearchParams(route.split('?')[1] ?? '');
  $: screen = parts[0] ?? '';
</script>

{#if db}
  <Rail {db} {screen} sectionId={parts[1] ?? null} />
{/if}
<main class="main" class:paper={screen === ''}>
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
{:else if screen === 'demo'}
  <Demo {db} step={Number(parts[1] ?? 1)} />
{:else if screen === 'welcome'}
  <Welcome />
{:else if screen === 'profile'}
  <Profile />
{:else if screen === 'volume'}
  <Volume {db} id={parts[1]} initialPage={Number(params.get('page') ?? 1)} highlight={params.get('passage')} />
{:else}
  <Library {db} />
{/if}
</main>

<nav class="nav" class:paper={screen === ''}>
  <a href="#/" class:on={screen === ''}>Library</a>
  <a href="#/recent" class:on={screen === 'recent'}>Recent</a>
  <a href="#/search" class:on={screen === 'search'}>Search</a>
  <a href="#/digest" class:on={screen === 'digest'}>Digest{#if queued().length}<span class="dot"></span>{/if}</a>
  <button class="net" class:off={!$online} title={$forceOffline ? 'Back online' : 'Simulate offline'} aria-label={$forceOffline ? 'Back online' : 'Simulate offline'} on:click={() => forceOffline.update((v) => !v)}></button>
</nav>
