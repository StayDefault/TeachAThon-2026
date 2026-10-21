import { useSyncExternalStore } from 'react';

/**
 * Voice loudness (0..1) changes ~12×/s. It lives outside the main store so only
 * the orb and waveform re-render, not the whole map.
 */
let level = 0;
const listeners = new Set<() => void>();

export function setLevel(next: number) {
  level = next;
  listeners.forEach((l) => l());
}

export function useLevel(): number {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => level,
  );
}
