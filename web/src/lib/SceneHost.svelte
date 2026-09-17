<script lang="ts">
  // Chooses the backdrop: at 900 px and wider, after the first paint, the three.js scene
  // (loaded on demand, so phones never download it); otherwise, or when the scene
  // cannot start, the fragment shader in Backdrop.svelte.
  import { onMount, type ComponentType } from 'svelte';
  import Backdrop from './Backdrop.svelte';

  export let animated = false;
  export let light = false;
  /** The section accent as a hex string; null means the home teal. */
  export let accent: string | null = null;

  let Scene: ComponentType | null = null;
  let wide = false;

  onMount(() => {
    const query = matchMedia('(min-width: 900px)');
    const decide = () => {
      wide = query.matches;
      if (wide && !Scene) {
        // After the first paint: two frames from now.
        requestAnimationFrame(() =>
          requestAnimationFrame(async () => {
            try {
              Scene = (await import('./Scene.svelte')).default as ComponentType;
            } catch {
              Scene = null;
            }
          }),
        );
      }
    };
    decide();
    query.addEventListener('change', decide);
    return () => query.removeEventListener('change', decide);
  });
</script>

{#if wide && Scene}
  {#key animated}<svelte:component this={Scene} {accent} {light} home={animated} />{/key}
{:else}
  {#key animated + String(light)}<Backdrop {animated} {light} />{/key}
{/if}
