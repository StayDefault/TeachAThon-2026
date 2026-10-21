import type { ClientEvent, ServerEvent, VoiceStatus } from '../types';
import type { DysCoverBackend, LiveConnection } from './backend';
import { createPcmPlayer, startMic, type MicHandle } from '../lib/audio';

/**
 * Real backend client. Endpoints and message formats are specified in docs/API.md.
 *
 * REST  : POST/GET /api/sessions..., JSON
 * Live  : WebSocket /api/sessions/:id/live
 *           text frames   = JSON ServerEvent / ClientEvent
 *           binary frames = audio (mic PCM16 16 kHz up, assistant PCM16 24 kHz down)
 */
export function createHttpBackend(base = ''): DysCoverBackend {
  const url = (p: string) => `${base}/api${p}`;

  async function json<T>(res: Response): Promise<T> {
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return res.json() as Promise<T>;
  }

  return {
    async createSession(files) {
      const form = new FormData();
      files.forEach((f) => form.append('files', f, f.name));
      return json(await fetch(url('/sessions'), { method: 'POST', body: form }));
    },
    async listSessions() {
      return json(await fetch(url('/sessions')));
    },
    async getSession(id) {
      return json(await fetch(url(`/sessions/${encodeURIComponent(id)}`)));
    },
    async getNodeDetail(sessionId, nodeId) {
      return json(await fetch(url(`/sessions/${encodeURIComponent(sessionId)}/nodes/${encodeURIComponent(nodeId)}`)));
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
  let status: VoiceStatus = 'connecting';
  let assistantPlaying = false;
  onEvent({ type: 'voice.status', status });

  // Orb level: the assistant's playback while it talks, otherwise the mic.
  const player = createPcmPlayer({
    onLevel: (level) => {
      assistantPlaying = level > 0.02;
      if (assistantPlaying) onEvent({ type: 'voice.level', level });
    },
  });

  ws.onopen = async () => {
    try {
      mic = await startMic({
        onChunk: (pcm) => {
          if (ws.readyState === WebSocket.OPEN && status !== 'ended') ws.send(pcm);
        },
        onLevel: (level) => {
          if (!assistantPlaying) onEvent({ type: 'voice.level', level });
        },
      });
    } catch (err) {
      onEvent({ type: 'error', message: `Microphone unavailable: ${String(err)}` });
    }
  };

  ws.onmessage = (msg) => {
    if (typeof msg.data !== 'string') {
      player.enqueue(msg.data as ArrayBuffer);
      return;
    }
    const event = JSON.parse(msg.data) as ServerEvent;
    if (event.type === 'voice.status') {
      status = event.status;
      // Barge-in: when the server says the learner started talking, cut the assistant's audio.
      if (status === 'listening') player.flush();
    }
    onEvent(event);
  };

  ws.onerror = () => onEvent({ type: 'error', message: 'Connection error' });
  ws.onclose = () => onEvent({ type: 'voice.status', status: 'ended' });

  return {
    send(event: ClientEvent) {
      if (event.type === 'session.end') {
        status = 'ended';
        mic?.setMuted(true);
        player.flush();
      }
      if (event.type === 'session.resume') {
        status = 'listening';
        mic?.setMuted(false);
      }
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(event));
    },
    close() {
      mic?.stop();
      player.close();
      ws.close();
    },
  };
}
