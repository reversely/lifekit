<script lang="ts">
  // The network state as a switch: every place that shows Online or Offline flips the
  // simulated-offline override, so the state is never a plain label.
  import Icon from './Icon.svelte';
  import { forceOffline, online } from './core/net';
  export let size = 16;
  export let iconOnly = false;
</script>

<button
  class="net"
  class:off={!$online}
  class:icon-only={iconOnly}
  aria-pressed={$forceOffline}
  aria-label={$forceOffline ? 'Back online' : 'Simulate offline'}
  title={$forceOffline ? 'Back online' : 'Simulate offline'}
  on:click={() => forceOffline.update((v) => !v)}
>
  <Icon name={$online ? 'wifi' : 'wifi-off'} {size} />{#if !iconOnly}<span>{$online ? 'Online' : 'Offline'}</span>{/if}
</button>
