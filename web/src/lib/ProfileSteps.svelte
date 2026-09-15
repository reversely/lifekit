<script lang="ts">
  // One onboarding question: options as chips, multi-select where the question allows it.
  import type { ProfileAnswers, ProfileQuestion } from './core/api';
  export let question: ProfileQuestion;
  export let profile: ProfileAnswers;
  export let onChange: (key: ProfileQuestion['key'], value: string | string[] | null) => void;

  $: current = profile[question.key];
  const selected = (value: string) => (Array.isArray(current) ? current.includes(value) : current === value);

  function pick(value: string) {
    if (!question.multi) {
      onChange(question.key, current === value ? null : value);
      return;
    }
    const list = Array.isArray(current) ? [...current] : [];
    const i = list.indexOf(value);
    if (i >= 0) list.splice(i, 1);
    else list.push(value);
    onChange(question.key, list);
  }
</script>

<div class="chips">
  {#each question.options as o}
    <button class="chip" class:on={selected(o.value)} on:click={() => pick(o.value)}>{o.label}</button>
  {/each}
</div>
