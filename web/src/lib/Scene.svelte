<script lang="ts">
  // The three.js scene behind desktop screens, per docs/content/biome-scene.md.
  // Planes: a full-viewport quad running the still shader (gradient, glow, rays, grain);
  // three ridge meshes at z = -6, -4, -2; fog from z = -1 to -8; 120 fireflies as points;
  // one point light behind the glow position. The camera moves down by a small fraction
  // of the page scroll. Colours derive from the section's accent against one deep base.
  import { onMount } from 'svelte';
  import * as THREE from 'three';

  /** The section accent as a hex string; null means the home teal. */
  export let accent: string | null = null;
  export let light = false;
  // On the home the ridges rise into the lower half as in the animated shader; on every
  // other screen they stay in the bottom fifth, clear of the reading area, as in the still one.
  export let home = false;

  const HOME = { accent: '#35576B', glow: '#8FC6BF', mote: '#B5E3DC' };
  const DEEP_TOP = '#0B1118';
  const DEEP_BASE = '#060A0D';
  const PAPER_TOP = '#F2F4F5';
  const PAPER_BASE = '#E6EBEE';

  // Mix in sRGB, for shader uniforms and CSS-side roles.
  const channel = (hex: string, i: number) => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16);
  const mixHex = (a: string, b: string, t: number) =>
    '#' + [0, 1, 2].map((i) => Math.round(channel(a, i) * (1 - t) + channel(b, i) * t).toString(16).padStart(2, '0')).join('');
  const rgb = (hex: string) => new THREE.Vector3(channel(hex, 0) / 255, channel(hex, 1) / 255, channel(hex, 2) / 255);

  interface Roles {
    top: string;
    bottom: string;
    glow: string;
    fog: string;
    terrain: string;
    mote: string;
  }
  // The six roles from one accent, the biome engine ratios in sRGB.
  function rolesFor(hex: string | null, paper: boolean): Roles {
    const a = hex ?? HOME.accent;
    if (paper) {
      return {
        top: PAPER_TOP,
        bottom: PAPER_BASE,
        glow: hex ? mixHex(a, '#ffffff', 0.2) : HOME.glow,
        fog: mixHex(a, PAPER_BASE, 0.94),
        terrain: mixHex(a, PAPER_BASE, 0.9),
        mote: mixHex(a, '#ffffff', 0.35),
      };
    }
    return {
      top: mixHex(a, DEEP_TOP, 0.9),
      bottom: mixHex(a, DEEP_BASE, 0.95),
      glow: hex ? mixHex(a, '#ffffff', 0.2) : HOME.glow,
      fog: mixHex(a, DEEP_BASE, 0.93),
      terrain: mixHex(a, DEEP_BASE, 0.9),
      mote: hex ? mixHex(a, '#ffffff', 0.35) : HOME.mote,
    };
  }
  // Ridge colours: the terrain role, mixed toward the gradient top for the far ridge and
  // toward the gradient base for the near ridge (docs/content/biome-scene.md 3), then the
  // accent added at linear quarter strength so the light picks out the facets.
  function materialTint(r: Roles, hex: string | null, paper: boolean, toward: 'top' | 'bottom' | 'none', amount: number): THREE.Color {
    const terrain = new THREE.Color(r.terrain);
    if (toward !== 'none') terrain.lerp(new THREE.Color(toward === 'top' ? r.top : r.bottom), amount);
    const tint = new THREE.Color(hex ?? HOME.accent).multiplyScalar(paper ? 0.01 : 0.02);
    return terrain.add(tint);
  }

  // The still shader from Backdrop.svelte (PageBackdrop.tsx, line for line) on a quad.
  const VERT = 'void main() { gl_Position = vec4(position.xy, 0.0, 1.0); }';
  const FRAG = `precision highp float;
uniform vec2 res; uniform vec3 top; uniform vec3 bottom; uniform vec3 glow; uniform vec3 terrain; uniform float strength;
float hash(float n) { return fract(sin(n * 127.1) * 43758.5453); }
float ridge(float x, float seed, float base, float amp) {
  float seg = floor(x * 6.0);
  float f = fract(x * 6.0);
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
  vec3 col = mix(top, bottom, smoothstep(0.0, 1.0, uv.y));
  float d = distance(uv * vec2(1.0, 1.7), vec2(0.5, 0.06));
  col += glow * exp(-d * d * 7.0) * 0.06 * strength;
  float rays = ray(uv, -0.12, -0.30, 0.040) + ray(uv, 0.02, 0.04, 0.060) + ray(uv, 0.15, 0.34, 0.040);
  col += glow * rays * 0.04 * strength;
  float grain = hash(xy.x + xy.y * 311.7) - 0.5;
  col += grain * 0.02;
  gl_FragColor = vec4(col, 1.0);
}`;

  // The ridge function from the shaders, sampled to a closed polygon: the top edge is
  // the ridge, the bottom edge sits below the frustum.
  const hash = (n: number) => {
    const x = Math.sin(n * 127.1) * 43758.5453;
    return x - Math.floor(x);
  };
  const ridge = (x: number, seed: number, base: number, amp: number) => {
    const seg = Math.floor(x * 7);
    const f = x * 7 - seg;
    const a = hash(seg + seed * 91.7);
    const b = hash(seg + 1 + seed * 91.7);
    return base + amp * (a * (1 - f) + b * f);
  };
  // A ridge is a grid of triangles: columns across the width, rows from the ridge line
  // down to below the frustum. Every vertex carries its own depth offset, so flat shading
  // gives each triangle a distinct normal and the lamp picks out facets.
  function ridgeGeometry(seed: number, width: number, height: number, base: number, amp: number): THREE.BufferGeometry {
    const cols = 48;
    const rows = 6;
    const positions: number[] = [];
    const vertex = (c: number, r: number) => {
      const t = c / cols;
      const top = (ridge(t, seed, base, amp) - 0.5) * height;
      const bottom = -height;
      const y = top + (bottom - top) * (r / rows);
      const jitter = (hash(c * 13.1 + r * 7.7 + seed * 31.3) - 0.5) * height * 0.12;
      return [-width / 2 + t * width, y, jitter * (1 - r / rows)];
    };
    for (let c = 0; c < cols; c++) {
      for (let r = 0; r < rows; r++) {
        const a = vertex(c, r), b = vertex(c + 1, r), d = vertex(c, r + 1), e = vertex(c + 1, r + 1);
        positions.push(...a, ...d, ...b, ...b, ...d, ...e);
      }
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.computeVertexNormals();
    return geometry;
  }

  // Fireflies: 120 points, each with its own phase and speed, drifting upward and
  // flickering at two periods that never line up (docs/content/biome-scene.md 3).
  const FIRE_VERT = `attribute float phase; attribute float speed; uniform float time; uniform float pixelRatio; uniform float still;
varying float vFlicker;
void main() {
  vec3 p = position;
  float t = time * (1.0 - still);
  p.y = mod(p.y + t * speed * 0.15, 6.0) - 3.0;
  p.x += sin(t * 0.3 + phase) * 0.15;
  vFlicker = 0.35 + 0.65 * abs(sin(t * (0.6 + fract(phase)) + phase * 2.0));
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_PointSize = (2.0 + 4.0 * fract(phase * 7.0)) * pixelRatio * (6.0 / -mv.z);
  gl_Position = projectionMatrix * mv;
}`;
  const FIRE_FRAG = `uniform vec3 mote; varying float vFlicker;
void main() {
  float d = length(gl_PointCoord - 0.5);
  float a = smoothstep(0.5, 0.0, d) * vFlicker;
  gl_FragColor = vec4(mote, a);
}`;

  let canvas: HTMLCanvasElement;
  let failed = false;

  onMount(() => {
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'low-power'});
    } catch {
      failed = true;
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.autoClear = false;
    const reduce = matchMedia('(prefers-reduced-motion: reduce)');

    // Background quad: an orthographic pass with the still shader.
    const bgScene = new THREE.Scene();
    const bgCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const bgMaterial = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      uniforms: {
        res: { value: new THREE.Vector2(1, 1) },
        top: { value: new THREE.Vector3() },
        bottom: { value: new THREE.Vector3() },
        glow: { value: new THREE.Vector3() },
        terrain: { value: new THREE.Vector3() },
        strength: { value: 1 },
      },
      depthTest: false,
      depthWrite: false,
    });
    bgScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), bgMaterial));

    // The main scene: ridges, fog, fireflies, light.
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 20);
    camera.position.set(0, 0, 0);
    const fog = new THREE.Fog(0x000000, 1, 8);
    scene.fog = fog;

    // Each ridge is wide enough to fill the frustum at its depth at any aspect ratio.
    // Ridge heights follow the shader: the far ridge sits 38 percent up the frame, the
    // middle 28, the near 18. The far ridge mixes toward the gradient top, the middle
    // stays the terrain role, the near ridge mixes toward the gradient base.
    const ridgeSpecs: { seed: number; z: number; base: number; amp: number; toward: 'top' | 'bottom' | 'none'; amount: number }[] = home
      ? [
          { seed: 3, z: -6, base: 0.38, amp: 0.12, toward: 'top', amount: 0.55 },
          { seed: 5, z: -4, base: 0.28, amp: 0.11, toward: 'none', amount: 0 },
          { seed: 7, z: -2, base: 0.18, amp: 0.1, toward: 'bottom', amount: 0.6 },
        ]
      : [
          { seed: 3, z: -6, base: 0.2, amp: 0.08, toward: 'top', amount: 0.5 },
          { seed: 7, z: -2, base: 0.1, amp: 0.06, toward: 'bottom', amount: 0.55 },
        ];
    const ridges = ridgeSpecs.map((spec) => {
      const height = 2 * Math.tan((camera.fov * Math.PI) / 360) * -spec.z;
      const width = height * 3;
      const mesh = new THREE.Mesh(
        ridgeGeometry(spec.seed, width, height, spec.base, spec.amp),
        new THREE.MeshStandardMaterial({ flatShading: true, roughness: 1, metalness: 0, emissiveIntensity: 1 }),
      );
      mesh.position.set(0, 0, spec.z);
      scene.add(mesh);
      return { mesh, spec };
    });

    const lamp = new THREE.PointLight(0xffffff, 1.8, 6, 2);
    lamp.position.set(0, 1.5, -3.5);
    scene.add(lamp);
    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambient);

    const COUNT = 120;
    const positions = new Float32Array(COUNT * 3);
    const phases = new Float32Array(COUNT);
    const speeds = new Float32Array(COUNT);
    for (let i = 0; i < COUNT; i++) {
      positions[i * 3] = (hash(i + 1) - 0.5) * 6;
      positions[i * 3 + 1] = (hash(i + 40) - 0.5) * 6;
      positions[i * 3 + 2] = -1.5 - hash(i + 80) * 5;
      phases[i] = hash(i + 120) * 6.283;
      speeds[i] = 0.5 + hash(i + 160);
    }
    const fireGeometry = new THREE.BufferGeometry();
    fireGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    fireGeometry.setAttribute('phase', new THREE.BufferAttribute(phases, 1));
    fireGeometry.setAttribute('speed', new THREE.BufferAttribute(speeds, 1));
    const fireMaterial = new THREE.ShaderMaterial({
      vertexShader: FIRE_VERT,
      fragmentShader: FIRE_FRAG,
      uniforms: {
        time: { value: 0 },
        pixelRatio: { value: renderer.getPixelRatio() },
        still: { value: reduce.matches ? 1 : 0 },
        mote: { value: new THREE.Color() },
      },
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    const fireflies = new THREE.Points(fireGeometry, fireMaterial);
    scene.add(fireflies);

    // Colour state: the current roles and the ones a crossfade moves toward, 900 ms.
    let current: Roles = rolesFor(accent, light);
    let target: Roles = current;
    let fadeStart = 0;
    const FADE = 900;
    const applied = { accent, light };
    const lerpHex = (a: string, b: string, t: number) => mixHex(a, b, t);
    function applyRoles(r: Roles, accentHex: string | null, paper: boolean) {
      bgMaterial.uniforms.top.value.copy(rgb(r.top));
      bgMaterial.uniforms.bottom.value.copy(rgb(r.bottom));
      bgMaterial.uniforms.glow.value.copy(rgb(r.glow));
      bgMaterial.uniforms.terrain.value.copy(rgb(r.terrain));
      bgMaterial.uniforms.strength.value = paper ? 0 : 1;
      fog.color.set(r.fog);
      lamp.color.set(r.glow);
      lamp.intensity = paper ? 0.3 : 1.8;
      ambient.color.set(r.top);
      ridges.forEach(({ mesh, spec }) => {
        // The role colour is the colour on screen (emissive); the lamp adds the facet highlights.
        const material = mesh.material as THREE.MeshStandardMaterial;
        material.emissive.copy(materialTint(r, accentHex, paper, spec.toward, spec.amount));
        material.color.copy(material.emissive);
      });
      fireMaterial.uniforms.mote.value.set(r.mote);
      fireflies.visible = !paper;
      if (canvas) canvas.dataset.tint = r.top; // the applied top colour, for a check to read
    }
    applyRoles(current, accent, light);

    // Rendering happens on scroll, on a tint change, and once per second for the
    // fireflies, capped at 30 frames per second, and not at all while the tab is hidden.
    let frames = 0;
    let scrollY = window.scrollY;
    let pending = false;
    let lastFrame = 0;
    let fading = false;
    const MIN_FRAME = 1000 / 30;
    let disposed = false;
    function render(now: number) {
      pending = false;
      if (disposed || document.hidden) return;
      if (now - lastFrame < MIN_FRAME) {
        request();
        return;
      }
      lastFrame = now;
      if (fading) {
        const t = Math.min(1, (now - fadeStart) / FADE);
        const mixed: Roles = {
          top: lerpHex(current.top, target.top, t),
          bottom: lerpHex(current.bottom, target.bottom, t),
          glow: lerpHex(current.glow, target.glow, t),
          fog: lerpHex(current.fog, target.fog, t),
          terrain: lerpHex(current.terrain, target.terrain, t),
          mote: lerpHex(current.mote, target.mote, t),
        };
        applyRoles(mixed, applied.accent, applied.light);
        if (t >= 1) {
          current = target;
          fading = false;
        } else request();
      }
      camera.position.y = -scrollY * 0.0008;
      fireMaterial.uniforms.time.value = reduce.matches ? 42 : now / 1000;
      renderer.clear();
      renderer.render(bgScene, bgCamera);
      renderer.render(scene, camera);
      canvas.dataset.frames = String(++frames);
    }
    function request() {
      if (pending) return;
      pending = true;
      requestAnimationFrame(render);
    }
    function resize() {
      const w = innerWidth;
      const h = innerHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      bgMaterial.uniforms.res.value.set(w * renderer.getPixelRatio(), h * renderer.getPixelRatio());
      request();
    }
    const onScroll = () => {
      scrollY = window.scrollY;
      request();
    };
    resize();
    addEventListener('resize', resize);
    addEventListener('scroll', onScroll, { passive: true });
    const onVisible = () => {
      if (!document.hidden) request();
    };
    document.addEventListener('visibilitychange', onVisible);
    // Once per second for the fireflies, unless motion is reduced.
    const timer = reduce.matches ? 0 : window.setInterval(() => request(), 1000);

    // Tint change: start a crossfade toward the new section's roles.
    const retint = () => {
      if (applied.accent === accent && applied.light === light) return;
      target = rolesFor(accent, light);
      applied.accent = accent;
      applied.light = light;
      fadeStart = performance.now();
      fading = true;
      request();
    };
    retintRef = retint;

    return () => {
      removeEventListener('resize', resize);
      removeEventListener('scroll', onScroll);
      document.removeEventListener('visibilitychange', onVisible);
      if (timer) clearInterval(timer);
      disposed = true;
      renderer.dispose();
      retintRef = null;
    };
  });

  let retintRef: (() => void) | null = null;
  $: accent, light, retintRef?.();
</script>

<canvas class="backdrop" class:failed bind:this={canvas} data-scene="three" aria-hidden="true"></canvas>
