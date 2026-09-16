<script lang="ts">
  // The world behind every screen: the flux HomeBackdrop (animated: glow, three god
  // rays, three faceted ridges with scroll parallax, drifting motes, grain) and the
  // PageBackdrop (still: glow, two ridges, grain), ported from SkSL to GLSL ES. One
  // fixed canvas; the still variant paints once and on resize.
  import { onMount } from 'svelte';
  export let animated = false;

  // HOME_BIOME from flux theme/biome.ts, as 0-1 triples.
  const rgb = (hex: string) => [0, 1, 2].map((i) => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16) / 255);
  const PALETTE = {
    top: rgb('#17252f'),
    bottom: rgb('#0c1319'),
    glow: rgb('#8FC6BF'),
    terrain: rgb('#0f1a20'),
    mote: rgb('#B5E3DC'),
  };

  const VERT = 'attribute vec2 a; void main() { gl_Position = vec4(a, 0.0, 1.0); }';
  const HEAD = `precision highp float;
uniform vec2 res; uniform float time; uniform float scroll;
uniform vec3 top; uniform vec3 bottom; uniform vec3 glow; uniform vec3 terrain; uniform vec3 mote;
float hash(float n) { return fract(sin(n * 127.1) * 43758.5453); }
`;
  // HomeBackdrop.tsx SRC, line for line.
  const HOME = HEAD + `
float ridge(float x, float seed, float base, float amp) {
  float seg = floor(x * 7.0);
  float f = fract(x * 7.0);
  float a = hash(seg + seed * 91.7);
  float b = hash(seg + 1.0 + seed * 91.7);
  return base + amp * mix(a, b, f);
}
float ray(vec2 uv, float offset, float slope, float width) {
  float x = uv.x - 0.5 - offset - uv.y * slope;
  float fall = 1.0 - smoothstep(0.0, 0.85, uv.y);
  return (1.0 - smoothstep(0.0, width, abs(x))) * fall;
}
void main() {
  vec2 xy = vec2(gl_FragCoord.x, res.y - gl_FragCoord.y);
  vec2 uv = xy / res;
  vec3 col = mix(top, bottom, smoothstep(0.05, 1.0, uv.y));
  float d = distance(uv * vec2(1.0, 1.6), vec2(0.5, 0.16));
  col += glow * exp(-d * d * 9.0) * 0.16;
  float rays = ray(uv, -0.12, -0.30, 0.040) + ray(uv, 0.02, 0.04, 0.060) + ray(uv, 0.15, 0.34, 0.040);
  col += glow * rays * 0.10;
  float farY = ridge(uv.x + scroll * 0.00002, 3.0, 0.62, 0.12);
  col = mix(col, mix(terrain, top, 0.55), smoothstep(farY, farY + 0.004, uv.y));
  float midY = ridge(uv.x + scroll * 0.00004 + 0.53, 5.0, 0.72, 0.11);
  col = mix(col, terrain, smoothstep(midY, midY + 0.004, uv.y));
  float nearY = ridge(uv.x + scroll * 0.00008 + 0.37, 7.0, 0.82, 0.10);
  col = mix(col, mix(terrain, bottom, 0.6), smoothstep(nearY, nearY + 0.003, uv.y));
  for (float i = 0.0; i < 9.0; i += 1.0) {
    vec2 p = vec2(hash(i + 1.0), hash(i + 40.0));
    p.y = fract(p.y * 0.8 + 0.1 - time * (0.008 + 0.012 * hash(i + 80.0)));
    p.x += sin(time * 0.3 + i) * 0.015;
    float flicker = 0.35 + 0.65 * abs(sin(time * (0.6 + hash(i)) + i * 2.0));
    float md = distance(uv * vec2(res.x / res.y, 1.0), p * vec2(res.x / res.y, 1.0));
    col += mote * exp(-md * md * 90000.0) * flicker * 0.35;
    col += mote * exp(-md * md * 9000.0) * flicker * 0.045;
  }
  float grain = hash(xy.x + xy.y * 311.7 + fract(time) * 17.0) - 0.5;
  col += grain * 0.025;
  gl_FragColor = vec4(col, 1.0);
}`;
  // PageBackdrop.tsx SRC, line for line.
  const PAGE = HEAD + `
float ridge(float x, float seed, float base, float amp) {
  float seg = floor(x * 6.0);
  float f = fract(x * 6.0);
  float a = hash(seg + seed * 91.7);
  float b = hash(seg + 1.0 + seed * 91.7);
  return base + amp * mix(a, b, f);
}
void main() {
  vec2 xy = vec2(gl_FragCoord.x, res.y - gl_FragCoord.y);
  vec2 uv = xy / res;
  vec3 col = mix(top, bottom, smoothstep(0.0, 1.0, uv.y));
  float d = distance(uv * vec2(1.0, 1.7), vec2(0.5, 0.06));
  col += glow * exp(-d * d * 7.0) * 0.13;
  float farY = ridge(uv.x, 3.0, 0.80, 0.10);
  col = mix(col, mix(terrain, top, 0.5), smoothstep(farY, farY + 0.004, uv.y));
  float nearY = ridge(uv.x + 0.37, 7.0, 0.90, 0.08);
  col = mix(col, mix(terrain, bottom, 0.55), smoothstep(nearY, nearY + 0.003, uv.y));
  float grain = hash(xy.x + xy.y * 311.7) - 0.5;
  col += grain * 0.02;
  gl_FragColor = vec4(col, 1.0);
}`;

  let canvas: HTMLCanvasElement;
  let failed = false;

  onMount(() => {
    const gl = canvas.getContext('webgl', { antialias: false, alpha: false, preserveDrawingBuffer: false });
    if (!gl) {
      failed = true;
      return;
    }
    const compile = (type: number, src: string) => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) ?? 'shader');
      return s;
    };
    let program: WebGLProgram;
    try {
      program = gl.createProgram()!;
      gl.attachShader(program, compile(gl.VERTEX_SHADER, VERT));
      gl.attachShader(program, compile(gl.FRAGMENT_SHADER, animated ? HOME : PAGE));
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error('link');
    } catch {
      failed = true;
      return;
    }
    gl.useProgram(program);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const a = gl.getAttribLocation(program, 'a');
    gl.enableVertexAttribArray(a);
    gl.vertexAttribPointer(a, 2, gl.FLOAT, false, 0, 0);
    const u = (name: string) => gl.getUniformLocation(program, name);
    for (const [name, value] of Object.entries(PALETTE)) gl.uniform3fv(u(name), value);

    const reduce = matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0;
    let scrollY = 0;
    const resize = () => {
      const dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = Math.round(innerWidth * dpr);
      canvas.height = Math.round(innerHeight * dpr);
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform2f(u('res'), canvas.width, canvas.height);
    };
    let frames = 0;
    const draw = (t: number) => {
      gl.uniform1f(u('time'), reduce.matches ? 42 : t / 1000);
      gl.uniform1f(u('scroll'), scrollY);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      canvas.dataset.frames = String(++frames); // a check can tell a live scene from a frozen one
    };
    const loop = (t: number) => {
      draw(t);
      frame = requestAnimationFrame(loop);
    };
    const onScroll = () => {
      scrollY = window.scrollY;
      if (!animated || reduce.matches) draw(42000);
    };
    resize();
    if (animated && !reduce.matches) frame = requestAnimationFrame(loop);
    else draw(42000);
    const onResize = () => {
      resize();
      if (!animated || reduce.matches) draw(42000);
    };
    addEventListener('resize', onResize);
    if (animated) addEventListener('scroll', onScroll, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      removeEventListener('resize', onResize);
      removeEventListener('scroll', onScroll);
    };
  });
</script>

<canvas class="backdrop" class:failed bind:this={canvas} aria-hidden="true"></canvas>
