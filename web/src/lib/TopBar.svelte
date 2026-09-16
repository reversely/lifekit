<script lang="ts">
  // The 56 px app bar from flux TopBar.tsx, laid transparently over the backdrop. An
  // inner screen gets a back chevron, its title, and the actions; the home gets a
  // centred row of icon buttons and no title, since the hero carries the wordmark.
  import Icon from './Icon.svelte';
  import NetToggle from './NetToggle.svelte';
  import ThemeToggle from './ThemeToggle.svelte';
  export let title = '';
  export let back = false;
  export let home = false;
  export let action: { icon: string; label: string; href: string } | null = null;
  export let paper = false;

  const goBack = () => (history.length > 1 ? history.back() : (location.hash = '#/'));
  const HOME_ACTIONS = [
    { icon: 'book-open', label: 'Library', href: '#/library' },
    { icon: 'layers', label: 'Recent', href: '#/recent' },
    { icon: 'search', label: 'Search', href: '#/search' },
    { icon: 'activity', label: 'Digest', href: '#/digest' },
    { icon: 'clock', label: 'Chats', href: '#/chats' },
    { icon: 'help-circle', label: 'How it works', href: '#/demo/1' },
  ];
</script>

<header class="topbar" class:is-home={home} class:paper class:centered={home}>
  {#if back}
    <button class="action" aria-label="Back" on:click={goBack}><Icon name="chevron-left" /></button>
  {/if}
  {#if title}
    <span class="title">{title}</span>
  {:else if back}
    <span class="title"></span>
  {/if}
  <div class="actions">
    {#if home}
      {#each HOME_ACTIONS as a}
        <a class="action" href={a.href} aria-label={a.label} title={a.label}><Icon name={a.icon} /></a>
      {/each}
    {:else if action}
      <a class="action" href={action.href} aria-label={action.label} title={action.label}><Icon name={action.icon} /></a>
    {/if}
    <span class="action"><ThemeToggle iconOnly size={20} /></span>
    <span class="action"><NetToggle iconOnly size={20} /></span>
  </div>
</header>
