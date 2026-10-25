import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const players = [], events = [], microphones = [];
const audio = {
  createPcmPlayer(options) {
    const player = { options, chunks: [], flushes: 0, closed: false,
      enqueue(chunk) { this.chunks.push(chunk); }, flush() { this.flushes++; }, close() { this.closed = true; } };
    players.push(player);
    return player;
  },
  async startMic() {
    const mic = { stopped: false, stop() { this.stopped = true; } };
    microphones.push(mic);
    return mic;
  },
};
class Socket {
  static OPEN = 1;
  static last;
  readyState = 1;
  sent = [];
  constructor() { Socket.last = this; }
  send(data) { this.sent.push(JSON.parse(data)); }
  close() { this.onclose?.({ code: 1000 }); }
}
const previous = globalThis.WebSocket;
globalThis.WebSocket = Socket;
try {
  const source = readFileSync(new URL('../src/api/http.ts', import.meta.url), 'utf8');
  const javascript = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const exports = {};
  new Function('require', 'exports', javascript)(() => audio, exports);
  const connection = exports.createHttpBackend('https://example.test').connect('sample', event => events.push(event));
  const socket = Socket.last;
  const receive = event => socket.onmessage({ data: JSON.stringify(event) });
  connection.setInputMode('text');
  socket.onopen();
  await Promise.resolve();
  assert.equal(microphones.length, 0);
  connection.send({ type: 'user.text', text: 'Explain this concept' });
  assert.equal(socket.sent.at(-1).type, 'user.text');
  socket.readyState = 0;
  connection.send({ type: 'user.text', text: 'Cannot send yet' });
  assert.equal(events.at(-1).type, 'error');
  assert.match(events.at(-1).message, /wasn't sent/);
  socket.readyState = 1;

  receive({ type: 'voice.audio', sampleRate: 16000 });
  assert.equal(players[0].closed, true);
  assert.equal(players.at(-1).options.sampleRate, 16000);
  const player = players.at(-1);
  receive({ type: 'voice.status', status: 'thinking' });
  socket.onmessage({ data: new ArrayBuffer(640) });
  assert.equal(events.at(-1).status, 'speaking');
  player.options.onPlaybackEnd();
  assert.equal(events.at(-1).status, 'thinking');
  receive({ type: 'voice.status', status: 'listening' });
  assert.equal(player.flushes, 0);
  receive({ type: 'voice.interrupt' });
  assert.equal(player.flushes, 1);

  connection.setInputMode('voice');
  await Promise.resolve();
  assert.equal(microphones.length, 1);
  connection.setInputMode('text');
  assert.equal(microphones[0].stopped, true);
  connection.send({ type: 'session.end' });
  const chunks = player.chunks.length;
  socket.onmessage({ data: new ArrayBuffer(640) });
  assert.equal(player.chunks.length, chunks);
  player.options.onPlaybackEnd();
  assert.equal(events.at(-1).type, 'voice.level');
  connection.send({ type: 'user.text', text: 'Text still works while voice is paused' });
  assert.equal(socket.sent.at(-1).type, 'user.text');
  connection.close();
  assert.equal(player.closed, true);
} finally {
  globalThis.WebSocket = previous;
}
console.log('Live audio protocol checks passed.');
