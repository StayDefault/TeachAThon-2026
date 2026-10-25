import type { ClientEvent, ServerEvent, VoiceStatus } from '../types';
import type { DysCoverBackend, LiveConnection } from './backend';
import { createPcmPlayer, startMic, type MicHandle } from '../lib/audio';

export async function apiError(res: Response): Promise<Error> {
  if (res.status >= 500 && res.status !== 502 && res.status !== 503) {
    return new Error('Dyscover ran into a problem. Please try again.');
  }
  const body: unknown = await res.json().catch(() => null);
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string' && body.detail.trim()) {
    return new Error(body.detail);
  }
  return new Error('Dyscover could not complete that request. Please try again.');
}

/**
 * Real backend client. Endpoints and message formats are specified in docs/API.md.
 *
 * REST  : POST/GET /api/sessions..., JSON
 * Live  : WebSocket /api/sessions/:id/live
 *           text frames   = JSON ServerEvent / ClientEvent
 *           binary frames = audio (mic PCM16 16 kHz; output 24 kHz chained, 16 kHz Live)
 */
export function createHttpBackend(base = ''): DysCoverBackend {
  const url = (p: string) => `${base}/api${p}`;

  async function json<T>(res: Response): Promise<T> {
    if (!res.ok) throw await apiError(res);
    return res.json() as Promise<T>;
  }

  async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
    let res: Response;
    try {
      res = await fetch(url(path), init);
    } catch {
      throw new Error('Cannot reach the Dyscover server. Please try again.');
    }
    return json<T>(res);
  }

  return {
    async createSession(files) {
      const form = new FormData();
      files.forEach((f) => form.append('files', f, f.name));
      return fetchJson('/sessions', { method: 'POST', body: form });
    },
    async listSessions() {
      return fetchJson('/sessions');
    },
    async getSession(id) {
      return fetchJson(`/sessions/${encodeURIComponent(id)}`);
    },
    materialUrl(sessionId, materialId) {
      return url(`/sessions/${encodeURIComponent(sessionId)}/materials/${encodeURIComponent(materialId)}`);
    },
    async deleteSession(id) {
      let res: Response;
      try {
        res = await fetch(url(`/sessions/${encodeURIComponent(id)}`), { method: 'DELETE' });
      } catch {
        throw new Error('Cannot reach the Dyscover server. Please try again.');
      }
      if (!res.ok) throw await apiError(res);
    },
    async getNodeDetail(sessionId, nodeId) {
      return fetchJson(`/sessions/${encodeURIComponent(sessionId)}/nodes/${encodeURIComponent(nodeId)}`);
    },
    async getHistory(sessionId) {
      return fetchJson(`/sessions/${encodeURIComponent(sessionId)}/history`);
    },
    connect(sessionId, onEvent) {
      return connectLive(wsUrl(base, `/api/sessions/${encodeURIComponent(sessionId)}/live`), onEvent);
    },
  };
}

function wsUrl(base: string, path: string): string {
  const origin = base || window.location.origin;
  return origin.replace(/^http/, 'ws') + path;
}

function connectLive(address: string, onEvent: (e: ServerEvent) => void): LiveConnection {
  const ws = new WebSocket(address);
  ws.binaryType = 'arraybuffer';
  let mic: MicHandle | null = null;
  let micStarting = false;
  let inputMode: 'voice' | 'text' = 'voice';
  let status: VoiceStatus = 'connecting';
  let assistantPlaying = false;
  let closedByClient = false;
  let liveAudio = false;
  let thinking = false;
  const canCapture = () => status !== 'ended';
  onEvent({ type: 'voice.status', status });

  // Orb level: the assistant's playback while it talks, otherwise the mic.
  const playbackOptions = {
    onLevel: (level: number) => {
      assistantPlaying = level > 0.02;
      if (assistantPlaying) onEvent({ type: 'voice.level', level });
    },
    onPlaybackEnd: () => {
      if (liveAudio && status !== 'ended') {
        status = thinking ? 'thinking' : 'listening';
        onEvent({ type: 'voice.status', status });
      }
    },
  };
  let player = createPcmPlayer(playbackOptions);

  const startVoice = async () => {
    if (mic || micStarting || inputMode !== 'voice' || status === 'ended' || ws.readyState !== WebSocket.OPEN) return;
    micStarting = true;
    try {
      const handle = await startMic({
        onChunk: (pcm) => {
          if (ws.readyState === WebSocket.OPEN && status !== 'ended' && inputMode === 'voice') ws.send(pcm);
        },
        onLevel: (level) => {
          if (!assistantPlaying && inputMode === 'voice') onEvent({ type: 'voice.level', level });
        },
      });
      if (inputMode === 'voice' && canCapture() && ws.readyState === WebSocket.OPEN) mic = handle;
      else handle.stop();
    } catch (err) {
      onEvent({ type: 'error', message: `Microphone unavailable: ${String(err)}` });
    } finally {
      micStarting = false;
    }
  };

  ws.onopen = () => { void startVoice(); };

  ws.onmessage = (msg) => {
    if (typeof msg.data !== 'string') {
      if (status === 'ended') return;
      if (liveAudio) {
        status = 'speaking';
        onEvent({ type: 'voice.status', status });
      }
      player.enqueue(msg.data as ArrayBuffer);
      return;
    }
    const event = JSON.parse(msg.data) as ServerEvent;
    if (event.type === 'voice.audio') {
      liveAudio = true;
      player.close();
      player = createPcmPlayer({ ...playbackOptions, sampleRate: event.sampleRate });
    }
    if (event.type === 'voice.interrupt') player.flush();
    if (event.type === 'voice.status') {
      status = event.status;
      thinking = status === 'thinking';
      if (status === 'ended') {
        mic?.stop();
        mic = null;
        player.flush();
        onEvent({ type: 'voice.level', level: 0 });
      }
      // Barge-in: when the server says the learner started talking, cut the assistant's audio.
      if (status === 'listening' && !liveAudio) player.flush();
    }
    onEvent(event);
  };

  ws.onclose = (event) => {
    mic?.stop();
    player.close();
    if (closedByClient) return;
    const message = event.code === 4401 ? 'Your sign-in expired. Reload and sign in again.'
      : event.code === 4404 ? 'This study session is no longer available. Start a new session.'
      : event.code === 1008 ? 'This page cannot connect from its current address.'
      : 'Live connection lost. Check that the backend is running, then reload the page.';
    onEvent({ type: 'error', message });
    onEvent({ type: 'voice.status', status: 'ended' });
  };

  return {
    send(event: ClientEvent) {
      if (event.type === 'session.end') {
        status = 'ended';
        mic?.stop();
        mic = null;
        player.flush();
      }
      if (event.type === 'session.resume') {
        status = 'listening';
        void startVoice();
      }
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(event));
      else if (event.type === 'user.text') onEvent({ type: 'error', message: "Your message wasn't sent because the connection isn't ready. Please try again." });
    },
    setInputMode(mode) {
      inputMode = mode;
      if (mode === 'text') {
        mic?.stop();
        mic = null;
        onEvent({ type: 'voice.level', level: 0 });
      } else void startVoice();
    },
    close() {
      closedByClient = true;
      mic?.stop();
      player.close();
      ws.close();
    },
  };
}
