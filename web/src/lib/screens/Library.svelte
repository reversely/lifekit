<script lang="ts">
  // The contents directory on parchment, from the flux Encyclopedia directory: a numeral,
  // the title on a gold rule, the scope line, and a Feather icon per section.
  import { onMount } from 'svelte';
  import type { Database } from '../core/db';
  import { shelves } from '../core/queries';
  import { digest as fetchDigest, profile as fetchProfile } from '../core/api';
  import Icon from '../Icon.svelte';
  export let db: Database;
  $: list = shelves(db);
  let line = '';
  let summary: string | null = null;


  onMount(async () => {
    try {
      const d = await fetchDigest();
      const parts = [];
      if (d.added.length) parts.push(`${d.added.length} volume${d.added.length === 1 ? '' : 's'} added.`);
      if (d.candidates.length) parts.push(`${d.candidates.length} new download${d.candidates.length === 1 ? '' : 's'}.`);
      if (d.pending.length) parts.push(`${d.pending.length} question${d.pending.length === 1 ? '' : 's'} in progress.`);
      line = parts.join(' ') || 'Nothing new since the last sync.';
    } catch {
      line = 'The library on this box is not reachable.';
    }
    try {
      const p = await fetchProfile();
      summary = p.profile.updated_at ? p.summary || 'Set' : '';
    } catch {
      summary = null;
    }
  });
</script>

<div class="dir">
  <div class="screen">
    <div class="digest">
      <h2>Since you were last online</h2>
      <p>{line}</p>
    </div>
    {#if summary !== null}
      <a class="row profile" href="#/profile">
        <div class="n"></div>
        <div>
          <div class="t">Profile</div>
          <div class="s">{summary || 'Not set'}</div>
        </div>
        <div class="ic"><Icon name="user" size={18} /></div>
      </a>
    {/if}
    <a class="row" href="#/demo/1">
      <div></div>
      <div>
        <div class="t">How it works</div>
        <div class="s">Five stations show the ask, the offline ask, the loop, the curation, and the binder.</div>
      </div>
      <div class="ic"><Icon name="help-circle" size={18} /></div>
    </a>
    <div class="label">Contents</div>
    {#each list as s}
      <a class="row" href={`#/section/${s.id}`}>
        <div class="n">{s.order}</div>
        <div>
          <div class="t">{s.title}</div>
          <div class="s">{s.scopeLine}</div>
          {#if s.count}<div class="c some">{s.count} volume{s.count === 1 ? '' : 's'}</div>{:else}<div class="c">No volumes</div>{/if}
        </div>
        <div class="ic"><Icon name={s.icon} size={18} /></div>
      </a>
    {/each}
  </div>
</div>
