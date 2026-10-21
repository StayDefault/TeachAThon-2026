/**
 * Replay helper for "Hear it again" / play buttons.
 * Plays the recorded audio if the backend provided one, otherwise falls back to the
 * browser's built-in text-to-speech so the demo always makes a sound.
 */
let current: HTMLAudioElement | null = null;

export function replay(text: string, audioUrl?: string) {
  stopReplay();
  if (audioUrl) {
    current = new Audio(audioUrl);
    void current.play();
    return;
  }
  if ('speechSynthesis' in window) {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'en-GB';
    u.rate = 0.95; // a little slower: easier to follow
    window.speechSynthesis.speak(u);
  }
}

export function stopReplay() {
  current?.pause();
  current = null;
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
}
