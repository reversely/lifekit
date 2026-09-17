<script lang="ts">
  // Onboarding: one question per step, saved as answered, ending with what the library
  // will look for (docs/content/library-schema.md 1.7, deployments-and-approval.md).
  import { onMount } from 'svelte';
  import ProfileSteps from '../ProfileSteps.svelte';
  import { flush, profile as fetchProfile, saveProfile, sync, type Profile, type ProfileQuestion, type Seeded } from '../core/api';

  export const DISMISSED = 'lifekit.welcomeDone';

  let data: Profile | null = null;
  let step = 0;
  let seeded: Seeded[] = [];
  let saving = false;
  let starting = false;
  let error = '';

  $: questions = data?.questions ?? [];
  $: done = data !== null && step >= questions.length;
  $: q = questions[step] as ProfileQuestion | undefined;

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
    saving = true;
    try {
      const saved = await saveProfile({ [key]: value } as any);
      seeded = [...seeded, ...(saved.seeded ?? [])];
      data = { ...saved, seeded };
    } catch {
      error = 'Could not save. Try again.';
    }
    saving = false;
  }

  function finish() {
    try {
      localStorage.setItem(DISMISSED, '1');
    } catch {
      /* storage unavailable */
    }
  }

  function skip() {
    finish();
    location.hash = '#/library';
  }

  async function start() {
    finish();
    starting = true;
    try {
      await flush();
      await sync();
      dispatchEvent(new CustomEvent('lifekit:reload'));
    } catch {
      /* the digest shows what is pending */
    }
    starting = false;
    location.hash = '#/digest';
  }

  onMount(load);
</script>

<div class="screen">
  <div class="top">
    <h1>Welcome</h1>
    <span class="sub">{done ? 'Queue' : q ? `${step + 1} of ${questions.length}` : ''}</span>
  </div>

  {#if error}
    <div class="hint">{error}</div>
    <div class="askrow"><button class="chip" on:click={skip}>Open the library</button></div>
  {:else if !data}
    <div class="hint">Opening the profile.</div>
  {:else if q}
    <div class="group">{q.ask}</div>
    <ProfileSteps question={q} profile={data.profile} onChange={change} />
    <div class="askrow steps">
      {#if step > 0}<button class="chip" on:click={() => (step -= 1)}>Back</button>{/if}
      <button class="chip ask" on:click={() => (step += 1)} disabled={saving}>Next</button>
      <button class="chip" on:click={skip}>Skip</button>
    </div>
  {:else}
    {#if seeded.length}
      {#each seeded as s}
        <div class="res">
          <div class="src"><b>{s.reason}</b></div>
          <p>{s.text}</p>
        </div>
      {/each}
    {:else}
      <div class="hint">No questions yet. Each answer adds questions here.</div>
    {/if}
    <div class="askrow steps">
      <button class="chip" on:click={() => (step -= 1)}>Back</button>
      <button class="chip ask" on:click={start} disabled={starting}>{starting ? 'Starting' : 'Start'}</button>
    </div>
  {/if}
</div>
