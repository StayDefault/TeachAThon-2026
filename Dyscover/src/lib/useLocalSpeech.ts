import { useCallback, useEffect, useRef } from 'react';
import { useStore } from '../state/store';
import { setLevel } from '../state/level';

/**
 * Client-side "speech" for the Home screen, where no session (and no backend connection) exists yet.
 * Streams a caption word by word and pulses the orb. To make it audible, call a TTS service in speak().
 */
export function useLocalSpeech() {
  const { dispatch } = useStore();
  const timers = useRef<number[]>([]);

  const cancel = useCallback(() => {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current = [];
  }, []);

  useEffect(() => cancel, [cancel]);

  const speak = useCallback(
    (text: string, msPerWord = 95) => {
      cancel();
      const words = text.split(' ');
      dispatch({ type: 'local.voice', status: 'speaking' });
      words.forEach((_, i) => {
        timers.current.push(
          window.setTimeout(() => {
            dispatch({ type: 'local.caption', caption: { role: 'assistant', text: words.slice(0, i + 1).join(' '), final: i === words.length - 1 } });
            setLevel(0.35 + Math.random() * 0.6);
          }, i * msPerWord),
        );
      });
      timers.current.push(
        window.setTimeout(() => {
          setLevel(0.04);
          dispatch({ type: 'local.voice', status: 'listening' });
        }, words.length * msPerWord + 200),
      );
    },
    [cancel, dispatch],
  );

  return { speak, cancel };
}
