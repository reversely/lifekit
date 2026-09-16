// Light or dark. The choice persists in this browser; without one the system setting
// decides. The root element carries data-theme so the stylesheet redefines the tokens.

import { writable } from 'svelte/store';

export type Theme = 'dark' | 'light';
const KEY = 'lifekit.theme';

function initial(): Theme {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === 'dark' || saved === 'light') return saved;
  } catch {
    /* storage unavailable */
  }
  return typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export const theme = writable<Theme>(initial());
theme.subscribe((t) => {
  if (typeof document !== 'undefined') document.documentElement.setAttribute('data-theme', t);
  try {
    localStorage.setItem(KEY, t);
  } catch {
    /* storage unavailable */
  }
});

export const toggleTheme = () => theme.update((t) => (t === 'dark' ? 'light' : 'dark'));
