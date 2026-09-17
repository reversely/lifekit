<script lang="ts">
  // Video summarization, laid out as the NVIDIA VSS demo: the clip, the summarization
  // prompt, the object tracking prompt, Reset and Launch; then an Input and Output tab
  // pair where the output shows each step as it runs and then the report.
  import { onMount } from 'svelte';
  import { clips as fetchClips, config as fetchConfig, videoStream, type Clip, type VideoEvent } from '../core/api';

  let clipList: Clip[] = [];
  let clip = '';
  let model = '';
  let textModel = '';
  let defaults = { prompt: '', tracking: '' };
  let prompt = '';
  let tracking = '';
  let tab: 'input' | 'output' = 'input';
  let events: VideoEvent[] = [];
  let working = false;
  let reportText = '';
  let failure = '';
  let elapsed = 0;
  let ticker: ReturnType<typeof setInterval> | null = null;
  let startedAt = 0;

  onMount(async () => {
    try {
      const c = await fetchConfig();
      textModel = c.small;
      defaults = { prompt: c.questions?.vss_summary?.[0] ?? '', tracking: c.questions?.vss_tracking?.[0] ?? '' };
      prompt = defaults.prompt;
      tracking = defaults.tracking;
    } catch {
      /* the prompts stay empty and the reader types one */
    }
    try {
      const r = await fetchClips();
      clipList = r.clips;
      model = r.model;
      clip = clipList[0]?.name ?? '';
    } catch {
      clipList = [];
    }
  });

  function reset() {
    prompt = defaults.prompt;
    tracking = defaults.tracking;
    events = [];
    reportText = '';
    failure = '';
    tab = 'input';
  }

  async function launch() {
    if (!clip || !prompt.trim() || working) return;
    working = true;
    events = [];
    reportText = '';
    failure = '';
    tab = 'output';
    startedAt = performance.now();
    elapsed = 0;
    ticker = setInterval(() => (elapsed = Math.round((performance.now() - startedAt) / 1000)), 1000);
    try {
      await videoStream({ clip, prompt, tracking }, (e) => {
        events = [...events, e];
        if (e.step === 'done') reportText = e.text ?? '';
        if (e.step === 'failed') failure = e.text ?? 'The run failed.';
      });
    } catch (e) {
      failure = String(e);
    }
    if (ticker) clearInterval(ticker);
    ticker = null;
    working = false;
  }

  $: total = clipList.find((c) => c.name === clip)?.seconds ?? 0;
  $: chunksDone = events.filter((e) => e.step === 'chunk').length;
  $: secondsRead = Math.min(total, events.filter((e) => e.step === 'chunk').reduce((m, e) => Math.max(m, e.end ?? 0), 0));
  // The progress sentence names the program at work: ffmpeg cuts frames, the vision model
  // describes them, the text model writes the report.
  $: last = events[events.length - 1];
  $: stage = !last ? 'The run is starting.'
    : last.step === 'report' ? `${textModel || 'The text model'} is writing the report.`
    : last.step === 'frames' ? `${model} is describing ${stamp(last.start ?? 0)} to ${stamp(last.end ?? 0)}.`
    : 'ffmpeg is cutting frames.';
  const stamp = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  // The report is plain text: the first line is the title, "## " lines are time-range
  // headings, "- " lines are events.
  $: lines = reportText.split('\n').map((l) => l.trim()).filter(Boolean);
</script>

<div class="screen video">
  <div class="tabs" role="tablist">
    <button class="tab" class:on={tab === 'input'} role="tab" aria-selected={tab === 'input'} on:click={() => (tab = 'input')}>Input</button>
    <button class="tab" class:on={tab === 'output'} role="tab" aria-selected={tab === 'output'} on:click={() => (tab = 'output')}>Output</button>
  </div>

  {#if tab === 'input'}
    <section class="panel">
      <h2>Video input</h2>
      {#if clipList.length}
        <div class="clip-row">
          <select bind:value={clip} aria-label="Clip" disabled={working}>
            {#each clipList as c}<option value={c.name}>{c.name} ({stamp(c.seconds)})</option>{/each}
          </select>
        </div>
        {#key clip}
          <!-- svelte-ignore a11y-media-has-caption -->
          <video class="player" src={`/vss/${clip}`} controls preload="metadata"></video>
        {/key}
      {:else}
        <p class="hint">No clip is in packs/vss-demo. A clip is an .mp4 file there with a manifest row.</p>
      {/if}
    </section>

    <section class="panel">
      <h2>Summarization prompt</h2>
      <textarea bind:value={prompt} rows="6" maxlength="2000" disabled={working} aria-label="Summarization prompt"></textarea>
    </section>

    <section class="panel">
      <h2>Object tracking prompt</h2>
      <textarea bind:value={tracking} rows="2" maxlength="200" disabled={working} aria-label="Object tracking prompt"></textarea>
    </section>

    <div class="actions">
      <button class="chip" on:click={reset} disabled={working}>Reset</button>
      <button class="chip ask" on:click={launch} disabled={working || !clip || !prompt.trim()}>Launch</button>
    </div>
  {:else}
    <section class="panel output">
      <h2>Report</h2>
      {#if working}
        <div class="progress">
          <div class="bar"><div class="fill" style={`width:${total ? Math.round((secondsRead / total) * 100) : 0}%`}></div></div>
          <p>{stage} {stamp(secondsRead)} of {stamp(total)} is described after {elapsed} s.</p>
        </div>
      {/if}
      {#if failure}
        <p class="fail">{failure}</p>
      {/if}
      {#if reportText}
        <article class="report">
          {#each lines as line, i}
            {#if i === 0}<h3>{line}</h3>
            {:else if line.startsWith('## ')}<h4>{line.slice(3)}</h4>
            {:else if line.startsWith('- ')}<p class="event">{line.slice(2)}</p>
            {:else}<p>{line}</p>{/if}
          {/each}
        </article>
        <p class="meta">{model} described the clip in {events[events.length - 1]?.elapsed ?? elapsed} s.</p>
      {:else if events.length}
        <div class="res trail">
          {#each events as e}
            {#if e.step === 'chunk'}
              <div class="step done">{e.text}</div>
            {:else if e.step === 'frames'}
              <div class="step">ffmpeg cut {e.count} frames for {stamp(e.start ?? 0)} to {stamp(e.end ?? 0)}.</div>
            {:else if e.step === 'report'}
              <div class="step">{textModel || 'The text model'} is writing the report.</div>
            {/if}
          {/each}
        </div>
      {:else if !working}
        <p class="hint">Launch a run from the Input tab. The vision model describes each ten seconds of the clip, and the text model writes the title and summary of the report.</p>
      {/if}
    </section>
  {/if}
</div>
