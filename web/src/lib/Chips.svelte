<script lang="ts">
  import { SORTS, type SortKey, type TagCount } from './core/types';
  export let counts: TagCount[];
  export let active: string | null = null;
  export let sort: SortKey | null = null;
  export let namespaces: { key: string; label: string }[] = [
    { key: 'section', label: 'Section' },
    { key: 'type', label: 'Type' },
    { key: 'publisher', label: 'Publisher' },
  ];
  export let onFilter: (tag: string | null) => void = () => {};
  export let onSort: (key: SortKey) => void = () => {};
</script>

<div class="chips">
  {#if sort}
    <span class="lab">Sort</span>
    {#each SORTS as s}
      <button class="chip" class:on={s.key === sort} on:click={() => onSort(s.key)}>{s.label}</button>
    {/each}
  {/if}
  {#each namespaces as ns, i}
    {@const group = counts.filter((c) => c.namespace === ns.key)}
    {#if group.length}
      <span class="lab">{ns.label}</span>
      {#if i === 0}
        <button class="chip" class:on={!active} on:click={() => onFilter(null)}>All</button>
      {/if}
      {#each group as c}
        <button class="chip" class:on={c.tag === active} class:empty={c.count === 0} on:click={() => onFilter(c.tag)}>
          {c.label}<span class="n">{c.count}</span>
        </button>
      {/each}
    {/if}
  {/each}
</div>
