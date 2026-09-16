# The biome scene on desktop

This document fixes the three.js scene that replaces the fragment-shader backdrop at 900 px
and above: which sections take which accent, what the scene draws, and the render budget it
must hold. It follows the colour-theory skill's depth palette and the scroll-journey skill's
biome engine, both read on 2026-09-16, and the repo rules in CLAUDE.md.

## Summary

Every section owns one accent. Six colour roles derive from that accent against one shared
deep base, so the sky, the terrain, the glow, and the fireflies of a section share the same
near-black. Opening a section or one of its volumes crossfades the scene to that section's
roles over 900 ms. The home keeps the hand-tuned teal. Phones keep the fragment shader.

## Conventions

| Term | Names |
|---|---|
| accent | One hex colour per section, in packs/sections.tsv column `accent`. |
| roles | top, bottom, glow, fog, terrain, mote, derived from the accent by the biome engine ratios. |
| deep base | #0B1118 at the top and #060A0D at the bottom, shared by every mix. |
| plane | One of background, midground, foreground, focal, each with its own luminance and saturation slice. |

## 1. The twelve accents

The accents sit far enough apart in hue that a thumbnail tells adjacent sections apart, and
low enough in saturation that the largest plane stays dim.

| Section | Accent | Hue family |
|---|---|---|
| medicine | #6B3541 | rose |
| shelter | #5A4A35 | umber |
| fire | #7A4A2A | ember |
| water | #2F5A6B | teal blue |
| food | #4E5F2F | olive |
| poisonous-plants | #3F5A3A | moss |
| animals | #6B5A2F | ochre |
| tools | #4A4A55 | slate |
| direction | #2F3F6B | indigo |
| signaling | #6B2F2F | red brown |
| environments | #2F6B5A | sea green |
| hazards | #5A2F6B | violet |

The home and every screen outside a section use the teal the flux app hand-tuned
(accent #35576B, glow #8FC6BF, mote #B5E3DC). Text and cards carry no accent; the hue
reaches them through the translucent surface.

## 2. Role derivation

The web mirror of biome.ts derives the roles in sRGB for CSS variables. The scene derives
its material colours in linear space by scaling: tint = accent × 0.05 + deep base, so a
tint that reads at a quarter strength on screen stays a quarter, which the sRGB ratios do
not give in a linear renderer.

## 3. The scene

| Plane | Object | Material |
|---|---|---|
| Background | A full-viewport quad running the existing still shader (gradient, glow, rays, grain) | The shader, with the section's top, bottom, glow |
| Midground | Three ridge meshes: extruded polygons from the ridge function at seeds 3, 5, 7, at depths z = -6, -4, -2 | Flat-shaded, terrain role scaled in linear space; the far ridge mixed toward top, the near ridge toward bottom |
| Fog | Scene fog from z = -1 to -8 | The fog role |
| Focal | A points system of 120 fireflies with size attenuation, drifting upward, flickering at incommensurate periods | The mote role, additive blending |
| Light | One point light behind the glow position, intensity 1.8, distance 6, decay 2 | The glow role |

Scroll moves the camera down by a small fraction of the page scroll, so the three ridges
parallax at true depth. Nothing else moves the camera.

## 4. Render budget

- The scene renders on scroll, on a tint change, and once per second for the fireflies;
  the frame rate is capped at 30 and drops to zero when the tab is hidden.
- Under prefers-reduced-motion the fireflies hold still and the scene renders once.
- The three.js build is imported only at 900 px and above and only after the first paint;
  phones never load it. The added weight stays under 160 KB gzipped.
- A crossfade between sections takes 900 ms and interpolates the material colours; text and
  cards do not transition.
- Without WebGL the CSS gradient fallback stands in, as today.

## 5. Light mode

The light theme swaps the deep base for paper (#F2F4F5 top, #E6EBEE bottom), keeps the
section accents, scales the glow to a quarter of its dark strength, sets the terrain to a
mix of the accent toward paper at 0.85, and turns the fireflies off.

## 6. Data

The accents live in packs/sections.tsv and reach the web app through /api/config and the
shelf table; no accent is named in code. Adding a section means adding a row.
