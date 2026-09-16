<script lang="ts">
  import { onMount } from 'svelte';
  import type { Database } from '../core/db';
  import { shelves } from '../core/queries';
  import { digest as fetchDigest, profile as fetchProfile } from '../core/api';
  export let db: Database;
  $: list = shelves(db);
  let line = '';
  let summary: string | null = null;

  onMount(async () => {
    try {
      const d = await fetchDigest();
      const parts = [];
      if (d.added.length) parts.push(`${d.added.length} volume${d.added.length === 1 ? '' : 's'} added.`);
      if (d.candidates.length) parts.push(`${d.candidates.length} waiting for your verdict.`);
      if (d.pending.length) parts.push(`${d.pending.length} being looked for.`);
      line = parts.join(' ') || 'Nothing new.';
    } catch {
      line = 'Offline.';
    }
    try {
      const p = await fetchProfile();
      summary = p.profile.updated_at ? p.summary || 'Set up' : '';
    } catch {
      summary = null;
    }
  });
</script>

<div class="dir">
  <div class="screen">
    <div class="top"><h1>Library</h1></div>
    <div class="digest">
      <h2>Since you were last online</h2>
      <p>{line || '…'}</p>
    </div>
    {#if summary !== null}
      <a class="row profile" href="#/profile">
        <div class="n"></div>
        <div>
          <div class="t">{summary ? 'Profile' : 'Set up your profile'}</div>
          <div class="s">{summary || 'Where you live, what you do, who is with you.'}</div>
        </div>
        <div></div>
      </a>
    {/if}
    <a class="row" href="#/demo/1">
      <div></div>
      <div>
        <div class="t">How it works</div>
        <div class="s">Five stations: ask, ask offline, the loop, your verdict, the binder.</div>
      </div>
      <div></div>
    </a>
    <div class="label">CONTENTS</div>
    {#each list as s}
      <a class="row" href={`#/section/${s.id}`}>
        <div class="n">{s.order}</div>
        <div>
          <div class="t">{s.title}</div>
          <div class="s">{s.scopeLine}</div>
          {#if s.count}<div class="c some">{s.count} volumes</div>{:else}<div class="c">none yet</div>{/if}
        </div>
        <div></div>
      </a>
    {/each}
  </div>
</div>
