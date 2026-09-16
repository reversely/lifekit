<script lang="ts">
  import type { Database } from '../core/db';
  import Card from '../Card.svelte';
  import Chips from '../Chips.svelte';
  import { tagCounts, volumes } from '../core/queries';
  import { SECTIONS, type SortKey } from '../core/types';
  export let db: Database;
  export let id: string;

  $: index = SECTIONS.findIndex((s) => s.id === id);
  $: section = SECTIONS[index];
  let active: string | null = null;
  let sort: SortKey = 'latest';
  $: counts = tagCounts(db, id);
  $: list = section ? volumes(db, { tag: `section:${id}`, sort }).filter((v) => !active || v.tags.some((t) => t.tag === active)) : [];
</script>

{#if !section}
  <div class="screen"><div class="hint">No such section.</div></div>
{:else}
<div class="screen">
  <div class="top"><h1>{index + 1}. {section.title}</h1><span class="sub">{section.scope}</span></div>
  <Chips
    {counts}
    {active}
    {sort}
    namespaces={[{ key: 'type', label: 'Type' }, { key: 'publisher', label: 'Publisher' }]}
    onFilter={(t) => (active = t)}
    onSort={(k) => (sort = k)}
  />
  <div style="height:16px"></div>
  <div class="grid">
    {#each list as v}<Card volume={v} showTags={false} />{/each}
  </div>
  {#if !list.length}<div class="hint">No volumes on this shelf yet.</div>{/if}
</div>
{/if}
