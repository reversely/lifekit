<script lang="ts">
  // Light or dark: a button with the sun icon in dark mode and the moon in light mode.
  import Icon from './Icon.svelte';
  import { theme, toggleTheme } from './core/theme';
  export let size = 16;
  export let iconOnly = false;
  $: label = $theme === 'dark' ? 'Light mode' : 'Dark mode';
</script>

<button class="mode" class:icon-only={iconOnly} aria-label={label} title={label} on:click={toggleTheme}>
  <Icon name={$theme === 'dark' ? 'sun' : 'moon'} {size} />{#if !iconOnly}<span>{label}</span>{/if}
</button>
