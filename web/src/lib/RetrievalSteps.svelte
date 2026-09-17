<script lang="ts">
  // The online retrieval's steps for one pass, in the order they happened, in plain lines.
  import type { RetrievalEvent } from './core/api';
  import type { Database } from './core/db';
  import { sectionTitle as titleOf } from './core/sections';
  export let db: Database | null = null;
  export let events: RetrievalEvent[] = [];
  export let working = false;

  const sectionTitle = (id?: string) => (id ? (db ? titleOf(db, id) : id) : '');
  const line = (e: RetrievalEvent): string => {
    switch (e.step) {
      case 'start': return `Question: ${e.text}`;
      case 'named': return `Topic: ${e.topic}`;
      case 'searched': return `Searched offline Wikipedia: ${e.titles?.length ?? 0} articles`;
      case 'picked': return `Selected: ${(e.titles ?? []).join(', ')}`;
      case 'filed': return `Section: ${sectionTitle(e.section)}`;
      case 'pulled': return `Retrieved: ${e.title}`;
      case 'covered': return 'Wrote the cover';
      case 'resolved': return 'Answered from the retrieved pages';
      case 'exhausted': return `No match${e.reason ? `: ${e.reason}` : ''}`;
      case 'search_failed': return `Search failed (${e.source})`;
      case 'pull_failed': return `Could not pull ${e.title}`;
      default: return e.step;
    }
  };
  $: groups = events.filter((e) => !e.done).reduce((acc: { id: string; items: RetrievalEvent[] }[], e) => {
    const g = acc.find((x) => x.id === e.question);
    if (g) g.items.push(e);
    else acc.push({ id: e.question, items: [e] });
    return acc;
  }, []);
</script>

{#each groups as g}
  <div class="res trail">
    {#each g.items as e}
      {#if e.step === 'start'}
        <div class="src"><b>{e.text}</b>{#if e.origin?.startsWith('rule:')} <span class="from">from the profile</span>{/if}</div>
      {:else if e.step === 'resolved'}
        <div class="step done">{line(e)}</div>
        <p>{e.answer}</p>
        {#each e.pages ?? [] as p}
          <a class="open" href={`#/volume/${p.volume}?page=${p.page}&passage=${encodeURIComponent(p.passage)}`}>{p.title}, page {p.page}</a>
        {/each}
      {:else if e.step === 'pulled'}
        <div class="step">{line(e)} <a class="inline" href={`#/volume/${e.volume}`}>open</a></div>
      {:else}
        <div class="step">{line(e)}</div>
      {/if}
    {/each}
  </div>
{/each}
{#if working}<div class="hint">{events.length ? 'Retrieving.' : 'Sending stored questions.'}</div>{/if}
