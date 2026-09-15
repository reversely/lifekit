<script lang="ts">
  // The household profile as an editable list. Each change saves at once.
  import { onMount } from 'svelte';
  import ProfileSteps from '../ProfileSteps.svelte';
  import { profile as fetchProfile, saveProfile, type Profile, type ProfileQuestion, type Seeded } from '../core/api';

  let data: Profile | null = null;
  let seeded: Seeded[] = [];
  let error = '';

  async function load() {
    try {
      data = await fetchProfile();
    } catch {
      error = 'The library on this box is not reachable.';
    }
  }

  async function change(key: ProfileQuestion['key'], value: string | string[] | null) {
    if (!data) return;
    data = { ...data, profile: { ...data.profile, [key]: value } };
    try {
      const saved = await saveProfile({ [key]: value } as any);
      seeded = [...(saved.seeded ?? []), ...seeded];
      data = saved;
    } catch {
      error = 'Could not save. Try again.';
    }
  }

  onMount(load);
</script>

<div class="screen">
  <div class="top">
    <a class="back" href="#/">‹ Library</a>
    <h1>Profile</h1>
    <span class="sub">{data?.summary || 'Not set up yet'}</span>
  </div>

  {#if error}
    <div class="hint">{error}</div>
  {:else if data}
    {#each data.questions as q}
      <div class="group">{q.ask}</div>
      <ProfileSteps question={q} profile={data.profile} onChange={change} />
    {/each}
    {#if seeded.length}
      <div class="group">Added to look for</div>
      {#each seeded as s}
        <div class="res">
          <div class="src"><b>{s.reason}</b></div>
          <p>{s.text}</p>
        </div>
      {/each}
      <div class="askrow"><a class="chip" href="#/digest">Open the digest</a></div>
    {/if}
  {:else}
    <div class="hint">Opening…</div>
  {/if}
</div>
