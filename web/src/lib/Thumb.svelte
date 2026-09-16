<script lang="ts">
  // A volume's thumbnail. When the file is missing, a typographic tile takes its place
  // so no broken image ever shows.
  export let id: string;
  export let title = '';
  export let publisher = '';
  export let big = false;
  let failed = false;
  $: failed = false, id;
  const initial = (text: string) => (text.trim()[0] ?? '').toUpperCase();
</script>

{#if failed}
  <div class="thumb tile" class:big aria-hidden="true">
    <span class="i">{initial(publisher || title)}</span>
    <span class="t">{title.slice(0, big ? 60 : 28)}</span>
  </div>
{:else}
  <img class="thumb" class:big src={`/thumbs/${id}.png`} alt="" on:error={() => (failed = true)} />
{/if}
