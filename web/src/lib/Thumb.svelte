<script lang="ts">
  // A volume's thumbnail. When the file is missing, a placeholder book cover takes its
  // place: a grey book with a darker spine, the title centred in uppercase, the
  // publisher beneath, so no broken image ever shows.
  export let id: string;
  export let title = '';
  export let publisher = '';
  export let big = false;
  let failed = false;
  $: failed = false, id;
</script>

{#if failed}
  <div class="thumb book" class:big aria-hidden="true">
    <span class="spine"></span>
    <span class="face">
      <span class="t">{title}</span>
      <span class="p">{publisher.split(',')[0]}</span>
    </span>
  </div>
{:else}
  <img class="thumb" class:big src={`/thumbs/${id}.png`} alt="" on:error={() => (failed = true)} />
{/if}
