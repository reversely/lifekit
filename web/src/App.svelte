<script lang="ts">
  import { onMount } from 'svelte';
  import type { Database } from './lib/core/db';
  import { database, reload } from './lib/core/db';
  import { volume } from './lib/core/queries';
  import { sectionTitle } from './lib/core/sections';
  import Welcome from './lib/screens/Welcome.svelte';
  import Profile from './lib/screens/Profile.svelte';
  import { profile as fetchProfile } from './lib/core/api';
  import Home from './lib/screens/Home.svelte';
  import Library from './lib/screens/Library.svelte';
  import Recent from './lib/screens/Recent.svelte';
  import Section from './lib/screens/Section.svelte';
  import Search from './lib/screens/Search.svelte';
  import Volume from './lib/screens/Volume.svelte';
  import Digest from './lib/screens/Digest.svelte';
  import Demo from './lib/screens/Demo.svelte';
  import Chat from './lib/screens/Chat.svelte';
  import Chats from './lib/screens/Chats.svelte';
  import Rail from './lib/Rail.svelte';
  import TopBar from './lib/TopBar.svelte';
  import Backdrop from './lib/Backdrop.svelte';
  import BackOnline from './lib/BackOnline.svelte';
  import { theme } from './lib/core/theme';

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
        /* no API: stay home */
      }
    }
  });

  $: parts = route.split('?')[0].split('/').filter(Boolean);
  $: params = new URLSearchParams(route.split('?')[1] ?? '');
  $: screen = parts[0] ?? '';
  $: isHome = screen === '';

  const TITLES: Record<string, string> = {
    library: 'Library', recent: 'Recent', search: 'Search', digest: 'Digest', chat: 'Chat', chats: 'Chats',
    demo: 'How it works', welcome: 'Welcome', profile: 'Profile',
  };
  $: title =
    screen === 'section' ? (db ? sectionTitle(db, parts[1] ?? '') : 'Section')
    : screen === 'volume' ? (db && volume(db, parts[1] ?? '')?.title) || 'Volume'
    : TITLES[screen] ?? '';
  $: action = screen === 'chat' ? { icon: 'clock', label: 'Chats', href: '#/chats' } : screen === 'digest' ? null : { icon: 'activity', label: 'Digest', href: '#/digest' };
</script>

{#key isHome + $theme}<Backdrop animated={isHome} light={$theme === 'light'} />{/key}
<BackOnline {db} />
{#if db}
  <Rail {db} {screen} sectionId={parts[1] ?? null} />
{/if}
<TopBar home={isHome} back={!isHome} {title} action={isHome ? null : action} paper={screen === 'library'} />
<main class="main" class:paper={screen === 'library'}>
{#if !db}
  <div class="screen"><div class="hint">Opening the library.</div></div>
{:else if isHome}
  <Home />
{:else if screen === 'library'}
  <Library {db} />
{:else if screen === 'recent'}
  <Recent {db} />
{:else if screen === 'section'}
  <Section {db} id={parts[1]} />
{:else if screen === 'search'}
  <Search {db} initial={params.get('q') ?? ''} />
{:else if screen === 'digest'}
  <Digest {db} />
{:else if screen === 'chat'}
  <Chat id={parts[1] ?? null} ask={params.get('ask')} />
{:else if screen === 'chats'}
  <Chats />
{:else if screen === 'demo'}
  <Demo {db} step={Number(parts[1] ?? 1)} />
{:else if screen === 'welcome'}
  <Welcome />
{:else if screen === 'profile'}
  <Profile />
{:else if screen === 'volume'}
  <Volume {db} id={parts[1]} initialPage={Number(params.get('page') ?? 1)} highlight={params.get('passage')} />
{:else}
  <Home />
{/if}
</main>
