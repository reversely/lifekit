// Online state from the browser itself: navigator.onLine plus the online/offline events.
// Chrome's offline mode (DevTools, or puppeteer's setOfflineMode) drives the same signal.

import { readable } from 'svelte/store';

export const online = readable(typeof navigator === 'undefined' ? true : navigator.onLine, (set) => {
  const up = () => set(true);
  const down = () => set(false);
  addEventListener('online', up);
  addEventListener('offline', down);
  return () => {
    removeEventListener('online', up);
    removeEventListener('offline', down);
  };
});
