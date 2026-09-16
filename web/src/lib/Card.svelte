<script lang="ts">
  import type { Volume } from './core/types';
  import Thumb from './Thumb.svelte';
  export let volume: Volume;
  export let showTags = true;

  const shortCover = (text: string) =>
    (text || 'No cover yet.').replace(/\n/g, ' ').split(/(?<=[.!?])\s+/).slice(0, 2).join(' ');

  /** At most 64 characters, cut at a word boundary; the volume page shows the full title. */
  const shortTitle = (title: string, max = 64) => {
    if (title.length <= max) return title;
    const cut = title.slice(0, max).replace(/[\s,:;-]+\S*$/, '');
    return cut + '…';
  };
</script>

<a class="card" href={`#/volume/${volume.id}`}>
  <div class="head">
    <Thumb id={volume.id} title={volume.title} publisher={volume.publisher} />
    <div>
      <h2 title={volume.title}>{shortTitle(volume.title)}</h2>
      <div class="ed">{volume.publisher}, {volume.edition}</div>
      {#if volume.admission === 'staged'}<span class="tag new">New download</span>{/if}
    </div>
  </div>
  <p>{shortCover(volume.cover)}</p>
  {#if showTags}
    <div class="tags">
      {#each volume.tags.filter((t) => t.namespace !== 'section') as t}
        <span class="tag" class:hand={t.source === 'hand'}>{t.value}</span>
      {/each}
    </div>
  {/if}
  <div class="foot">{volume.pageCount} pages</div>
</a>
