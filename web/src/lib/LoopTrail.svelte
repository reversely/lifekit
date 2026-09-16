<script lang="ts">
  // The loop's steps for one pass, in the order they happened, in plain lines.
  import type { LoopEvent } from './core/api';
  import { SECTIONS } from './core/types';
  export let events: LoopEvent[] = [];
  export let working = false;

  const sectionTitle = (id?: string) => SECTIONS.find((s) => s.id === id)?.title ?? id ?? '';
  const line = (e: LoopEvent): string => {
    switch (e.step) {
      case 'start': return `Working on: ${e.text}`;
      case 'named': return `Topic named by the model: ${e.topic}`;
      case 'searched': return `Searched ${e.source}: ${e.titles?.length ?? 0} titles`;
      case 'picked': return `Model chose: ${(e.titles ?? []).join(', ')}`;
      case 'filed': return `Filed under ${sectionTitle(e.section)}`;
      case 'pulled': return `Pulled ${e.title}`;
      case 'covered': return 'Cover written';
      case 'resolved': return 'Answered from the new pages';
      case 'exhausted': return `Nothing found${e.reason ? `: ${e.reason}` : ''}`;
      case 'search_failed': return `Search failed (${e.source})`;
      case 'pull_failed': return `Could not pull ${e.title}`;
      default: return e.step;
    }
  };
  $: groups = events.filter((e) => !e.done).reduce((acc: { id: string; items: LoopEvent[] }[], e) => {
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
        <div class="src"><b>{e.text}</b>{#if e.origin?.startsWith('rule:')} <span class="from">from your profile</span>{/if}</div>
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
{#if working}<div class="hint">{events.length ? 'Working…' : 'Sending stored questions…'}</div>{/if}
