<script lang="ts">
  // Video summarization, laid out as the NVIDIA VSS demo: the source (a stored clip or
  // the laptop camera), the summarization prompt, the object tracking prompt, Reset and
  // Launch; then an Input and Output tab pair where the output shows each step as it runs
  // and then the report. A guided tour anchors a numbered callout to each control.
  import { onDestroy, onMount, tick } from 'svelte';
  import { clips as fetchClips, config as fetchConfig, videoReport, videoSegment, videoStream, type Clip, type TourStep, type VideoEvent } from '../core/api';

  const CAMERA = 'camera';
  const SEGMENT_MS = 10000;

  let clipList: Clip[] = [];
  let source = '';
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
  let cameraAvailable = false;
  let tourSteps: TourStep[] = [];

  onMount(async () => {
    cameraAvailable = typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined';
    try {
      const c = await fetchConfig();
      textModel = c.small;
      defaults = { prompt: c.questions?.vss_summary?.[0] ?? '', tracking: c.questions?.vss_tracking?.[0] ?? '' };
      prompt = defaults.prompt;
      tracking = defaults.tracking;
      tourSteps = c.video_tour ?? [];
    } catch {
      /* the prompts stay empty and the reader types one */
    }
    try {
      const r = await fetchClips();
      clipList = r.clips;
      model = r.model;
      source = clipList[0]?.name ?? (cameraAvailable ? CAMERA : '');
    } catch {
      clipList = [];
      source = cameraAvailable ? CAMERA : '';
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

  function startClock() {
    startedAt = performance.now();
    elapsed = 0;
    ticker = setInterval(() => (elapsed = Math.round((performance.now() - startedAt) / 1000)), 1000);
  }
  function stopClock() {
    if (ticker) clearInterval(ticker);
    ticker = null;
  }

  async function launch() {
    if (!source || !prompt.trim() || working) return;
    working = true;
    events = [];
    reportText = '';
    failure = '';
    if (source === CAMERA) {
      await record();
      return;
    }
    tab = 'output';
    startClock();
    try {
      await videoStream({ clip: source, prompt, tracking }, (e) => {
        events = [...events, e];
        if (e.step === 'done') reportText = e.text ?? '';
        if (e.step === 'failed') failure = e.text ?? 'The run failed.';
      });
    } catch (e) {
      failure = String(e);
    }
    stopClock();
    working = false;
  }

  // The camera: the browser records ten-second segments, one MediaRecorder per segment
  // so each segment is a complete file, and posts each to the API as it ends. Segments
  // are described in order while recording continues. Stop ends the recording and asks
  // for the report over every described segment.
  let stream: MediaStream | null = null;
  let preview: HTMLVideoElement | null = null;
  let recorder: MediaRecorder | null = null;
  let recording = false;
  let recordedSeconds = 0;
  let segmentIndex = 0;
  let uploads: Promise<void> = Promise.resolve();
  let notes: { start: number; end: number; text: string }[] = [];

  async function record() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
    } catch (e) {
      failure = `The camera did not open: ${String(e)}`;
      working = false;
      return;
    }
    recording = true;
    recordedSeconds = 0;
    segmentIndex = 0;
    notes = [];
    startClock();
    await tick();
    if (preview) preview.srcObject = stream;
    nextSegment();
  }

  function nextSegment() {
    if (!stream || !recording) return;
    const type = MediaRecorder.isTypeSupported('video/webm;codecs=vp8') ? 'video/webm;codecs=vp8' : MediaRecorder.isTypeSupported('video/webm') ? 'video/webm' : 'video/mp4';
    const r = new MediaRecorder(stream, { mimeType: type });
    const parts: Blob[] = [];
    const start = recordedSeconds;
    const index = segmentIndex++;
    r.ondataavailable = (e) => { if (e.data.size) parts.push(e.data); };
    r.onstop = () => {
      const blob = new Blob(parts, { type: type.split(';')[0] });
      recordedSeconds = start + SEGMENT_MS / 1000;
      events = [...events, { step: 'frames', start, end: recordedSeconds, count: 6, elapsed }];
      uploads = uploads.then(async () => {
        try {
          const note = await videoSegment(blob, { start, prompt, tracking });
          notes = [...notes, note];
          events = [...events, { step: 'chunk', start: note.start, end: note.end, text: note.text, elapsed }];
        } catch (e) {
          events = [...events, { step: 'failed', text: `Segment ${index + 1}: ${String(e)}` }];
        }
      });
      if (recording) nextSegment();
    };
    recorder = r;
    r.start();
    setTimeout(() => { if (r.state === 'recording') r.stop(); }, SEGMENT_MS);
  }

  async function stopRecording() {
    recording = false;
    if (recorder && recorder.state === 'recording') recorder.stop();
    stream?.getTracks().forEach((t) => t.stop());
    stream = null;
    tab = 'output';
    await tick();
    await uploads;
    events = [...events, { step: 'report', elapsed }];
    try {
      const r = await videoReport({ prompt, notes });
      reportText = r.text;
      events = [...events, { step: 'done', text: r.text, elapsed }];
      if (!r.text) failure = 'No segment was described, so there is no report.';
    } catch (e) {
      failure = String(e);
    }
    stopClock();
    working = false;
  }

  onDestroy(() => {
    recording = false;
    stream?.getTracks().forEach((t) => t.stop());
    stopClock();
  });

  $: total = source === CAMERA ? recordedSeconds : clipList.find((c) => c.name === source)?.seconds ?? 0;
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

  // The tour: one numbered callout at a time, anchored to the control its step names.
  let tourAt = -1;
  let anchorBox: { top: number; left: number; width: number; height: number } | null = null;
  $: tourStep = tourAt >= 0 ? tourSteps[tourAt] : null;
  async function tourGo(index: number) {
    if (index < 0 || index >= tourSteps.length) {
      tourAt = -1;
      anchorBox = null;
      document.querySelectorAll('.tour-on').forEach((e) => e.classList.remove('tour-on'));
      return;
    }
    tourAt = index;
    tab = tourSteps[index].anchor === 'report' ? 'output' : 'input';
    await tick();
    document.querySelectorAll('.tour-on').forEach((e) => e.classList.remove('tour-on'));
    const el = document.querySelector<HTMLElement>(`[data-tour="${tourSteps[index].anchor}"]`);
    if (!el) {
      anchorBox = null;
      return;
    }
    el.classList.add('tour-on');
    el.scrollIntoView({ block: 'center', behavior: 'instant' as ScrollBehavior });
    await tick();
    const r = el.getBoundingClientRect();
    anchorBox = { top: r.top, left: r.left, width: r.width, height: r.height };
  }
  // The callout sits below the anchor when there is room, else above it, and never past
  // the right edge of the viewport.
  $: calloutStyle = (() => {
    if (!anchorBox) return 'top: 96px; left: 50%; transform: translateX(-50%);';
    const width = Math.min(360, window.innerWidth - 32);
    const left = Math.max(16, Math.min(anchorBox.left, window.innerWidth - width - 16));
    const below = anchorBox.top + anchorBox.height + 12;
    const top = below + 180 < window.innerHeight ? below : Math.max(16, anchorBox.top - 192);
    return `top: ${top}px; left: ${left}px; width: ${width}px;`;
  })();
</script>

<div class="screen video" class:touring={tourAt >= 0}>
  <div class="tabs" role="tablist">
    <button class="tab" class:on={tab === 'input'} role="tab" aria-selected={tab === 'input'} on:click={() => (tab = 'input')}>Input</button>
    <button class="tab" class:on={tab === 'output'} role="tab" aria-selected={tab === 'output'} on:click={() => (tab = 'output')}>Output</button>
    {#if tourSteps.length}
      <button class="tour-open chip" on:click={() => tourGo(0)} disabled={tourAt >= 0}>Tour</button>
    {/if}
  </div>

  {#if tab === 'input'}
    <section class="panel">
      <h2>Video input</h2>
      {#if clipList.length || cameraAvailable}
        <div class="clip-row" data-tour="source">
          <select bind:value={source} aria-label="Source" disabled={working}>
            {#each clipList as c}<option value={c.name}>{c.name} ({stamp(c.seconds)})</option>{/each}
            {#if cameraAvailable}<option value={CAMERA}>Laptop camera</option>{/if}
          </select>
        </div>
        {#if source === CAMERA}
          <div class="capture">
            <!-- svelte-ignore a11y-media-has-caption -->
            <video class="player" bind:this={preview} autoplay muted playsinline></video>
            {#if recording}
              <span class="recording"><span class="dot"></span>Recording {stamp(elapsed)}</span>
            {:else}
              <p class="hint over">The camera preview appears here when the run starts.</p>
            {/if}
          </div>
        {:else}
          {#key source}
            <!-- svelte-ignore a11y-media-has-caption -->
            <video class="player" src={`/vss/${source}`} controls preload="metadata"></video>
          {/key}
        {/if}
      {:else}
        <p class="hint">No clip is in packs/vss-demo and this browser has no camera. A clip is an .mp4 file there with a manifest row.</p>
      {/if}
    </section>

    <section class="panel">
      <h2>Summarization prompt</h2>
      <textarea data-tour="prompt" bind:value={prompt} rows="6" maxlength="2000" disabled={working} aria-label="Summarization prompt"></textarea>
    </section>

    <section class="panel">
      <h2>Object tracking prompt</h2>
      <textarea data-tour="tracking" bind:value={tracking} rows="2" maxlength="200" disabled={working} aria-label="Object tracking prompt"></textarea>
    </section>

    <div class="actions" data-tour="launch">
      <button class="chip" on:click={reset} disabled={working}>Reset</button>
      {#if recording}
        <button class="chip ask" on:click={stopRecording}>Stop</button>
      {:else}
        <button class="chip ask" on:click={launch} disabled={working || !source || !prompt.trim()}>Launch</button>
      {/if}
    </div>
  {:else}
    <section class="panel output" data-tour="report">
      <h2>Report</h2>
      {#if working}
        <div class="progress">
          <div class="bar"><div class="fill" style={`width:${total ? Math.round((secondsRead / total) * 100) : 0}%`}></div></div>
          {#if recording}
            <p>The camera is recording. {stamp(secondsRead)} of {stamp(recordedSeconds)} is described after {elapsed} s. Stop on the Input tab ends the recording and writes the report.</p>
          {:else}
            <p>{stage} {stamp(secondsRead)} of {stamp(total)} is described after {elapsed} s.</p>
          {/if}
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
        <p class="meta">{model} described the video in {events[events.length - 1]?.elapsed ?? elapsed} s.</p>
      {:else if events.length}
        <div class="res trail">
          {#each events as e}
            {#if e.step === 'chunk'}
              <div class="step done">{e.text}</div>
            {:else if e.step === 'frames'}
              <div class="step">{source === CAMERA ? `The camera recorded ${stamp(e.start ?? 0)} to ${stamp(e.end ?? 0)}.` : `ffmpeg cut ${e.count} frames for ${stamp(e.start ?? 0)} to ${stamp(e.end ?? 0)}.`}</div>
            {:else if e.step === 'report'}
              <div class="step">{textModel || 'The text model'} is writing the report.</div>
            {:else if e.step === 'failed'}
              <div class="step fail">{e.text}</div>
            {/if}
          {/each}
        </div>
      {:else if !working}
        <p class="hint">Launch a run from the Input tab. The vision model describes each ten seconds of video, and the text model writes the title and summary of the report.</p>
      {/if}
    </section>
  {/if}

  {#if tourStep}
    <div class="callout" style={calloutStyle} role="dialog" aria-label={`Tour step ${tourAt + 1} of ${tourSteps.length}`}>
      <div class="callout-head"><span class="n">{tourAt + 1}</span><h3>{tourStep.title}</h3></div>
      <p>{tourStep.text}</p>
      <div class="callout-nav">
        <button class="chip" on:click={() => tourGo(tourAt - 1)} disabled={tourAt === 0}>Previous</button>
        <button class="chip go" on:click={() => tourGo(tourAt + 1)}>{tourAt + 1 === tourSteps.length ? 'Done' : 'Next'}</button>
      </div>
    </div>
  {/if}
</div>
