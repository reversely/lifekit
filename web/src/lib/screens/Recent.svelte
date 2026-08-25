<script lang="ts">
  import type { Database } from '../core/db';
  import Card from '../Card.svelte';
  import Chips from '../Chips.svelte';
  import { tagCounts, volumes } from '../core/queries';
  import type { SortKey } from '../core/types';
  export let db: Database;

  let active: string | null = null;
  let sort: SortKey = 'latest';
  $: list = volumes(db, { tag: active ?? undefined, sort });
  const counts = tagCounts(db);

  const dayOf = (iso: string) => iso.slice(0, 10);
  const dayLabel = (day: string) =>
    day ? new Date(day + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) : 'Undated';
</script>

<div class="screen">
  <div class="top"><h1>Recent</h1></div>
  <Chips {counts} {active} {sort} onFilter={(t) => (active = t)} onSort={(k) => (sort = k)} />
  <div class="grid">
    {#each list as v, i}
      {#if (sort === 'latest' || sort === 'oldest') && (i === 0 || dayOf(v.retrieved) !== dayOf(list[i - 1].retrieved))}
        <div class="day span">{dayLabel(dayOf(v.retrieved))}</div>
      {:else if i === 0}
        <div class="span" style="height:8px"></div>
      {/if}
      <Card volume={v} />
    {/each}
  </div>
</div>
