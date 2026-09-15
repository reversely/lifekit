// Online state: the browser's own signal (navigator.onLine plus the online/offline
// events) AND a switch the reader can flip to rehearse the offline path.

import { derived, writable } from 'svelte/store';

const KEY = 'lifekit.forceOffline';

const read = () => {
  try {
    return localStorage.getItem(KEY) === '1';
  } catch {
    return false;
  }
};

/** True while the reader has switched the app to offline on purpose. */
export const forceOffline = writable(read());
forceOffline.subscribe((v) => {
  try {
    localStorage.setItem(KEY, v ? '1' : '0');
  } catch {
    /* storage unavailable */
  }
});

const browserOnline = writable(typeof navigator === 'undefined' ? true : navigator.onLine);
if (typeof addEventListener === 'function') {
  addEventListener('online', () => browserOnline.set(true));
  addEventListener('offline', () => browserOnline.set(false));
}

export const online = derived([browserOnline, forceOffline], ([b, f]) => b && !f);
