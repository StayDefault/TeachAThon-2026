/**
 * Browser audio helpers for the real backend (not used by the mock).
 *
 *  - startMic(): captures the microphone as 16 kHz mono PCM16 chunks + a 0..1 loudness level.
 *  - createPcmPlayer(): plays PCM16 chunks streamed from the backend, gap-free, + a loudness level.
 *
 * Formats are the defaults in docs/API.md; change both sides together if the speech model needs others.
 */

export interface MicHandle {
  stop(): void;
  setMuted(muted: boolean): void;
}

export async function startMic(opts: {
  sampleRate?: number;
  onChunk: (pcm16: ArrayBuffer) => void;
  onLevel?: (level: number) => void;
}): Promise<MicHandle> {
  const sampleRate = opts.sampleRate ?? 16000;
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  const ctx = new AudioContext({ sampleRate });
  const source = ctx.createMediaStreamSource(stream);
  // ScriptProcessorNode is deprecated but universally supported and simple.
  // Swap for an AudioWorklet if you need lower latency.
  const proc = ctx.createScriptProcessor(2048, 1, 1);
  let muted = false;

  proc.onaudioprocess = (e) => {
    const input = e.inputBuffer.getChannelData(0);
    opts.onLevel?.(rms(input));
    if (muted) return;
    opts.onChunk(floatToPcm16(input));
  };
  source.connect(proc);
  proc.connect(ctx.destination); // required in some browsers for onaudioprocess to fire

  return {
    stop() {
      proc.disconnect();
      source.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      void ctx.close();
    },
    setMuted(m) {
      muted = m;
    },
  };
}

export interface PcmPlayer {
  enqueue(pcm16: ArrayBuffer): void;
  /** Stop playback immediately (e.g. the learner interrupts). */
  flush(): void;
  close(): void;
}

export function createPcmPlayer(opts: { sampleRate?: number; onLevel?: (level: number) => void } = {}): PcmPlayer {
  const sampleRate = opts.sampleRate ?? 24000;
  const ctx = new AudioContext({ sampleRate });
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 512;
  analyser.connect(ctx.destination);
  let playhead = 0;
  let sources: AudioBufferSourceNode[] = [];
  const buf = new Float32Array(analyser.fftSize);

  const raf = () => {
    analyser.getFloatTimeDomainData(buf);
    opts.onLevel?.(rms(buf));
    handle = requestAnimationFrame(raf);
  };
  let handle = requestAnimationFrame(raf);

  return {
    enqueue(pcm16) {
      const samples = pcm16ToFloat(pcm16);
      const audio = ctx.createBuffer(1, samples.length, sampleRate);
      audio.copyToChannel(samples, 0);
      const src = ctx.createBufferSource();
      src.buffer = audio;
      src.connect(analyser);
      playhead = Math.max(playhead, ctx.currentTime + 0.02);
      src.start(playhead);
      playhead += audio.duration;
      sources.push(src);
      src.onended = () => (sources = sources.filter((s) => s !== src));
    },
    flush() {
      sources.forEach((s) => s.stop());
      sources = [];
      playhead = 0;
    },
    close() {
      cancelAnimationFrame(handle);
      this.flush();
      void ctx.close();
    },
  };
}

function rms(data: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
  // Scale so normal speech lands around 0.3–0.9.
  return Math.min(1, Math.sqrt(sum / data.length) * 6);
}

function floatToPcm16(input: Float32Array): ArrayBuffer {
  const out = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out.buffer;
}

function pcm16ToFloat(buf: ArrayBuffer): Float32Array {
  const int = new Int16Array(buf);
  const out = new Float32Array(int.length);
  for (let i = 0; i < int.length; i++) out[i] = int[i] / 0x8000;
  return out;
}
