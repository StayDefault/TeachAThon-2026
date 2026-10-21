import type { ClientEvent, MapNode, Material, MaterialKind, ServerEvent } from '../types';
import type { DysCoverBackend, LiveConnection } from './backend';
import {
  DEMO_MATERIALS,
  DEMO_SESSIONS,
  FINISHED_MAP,
  KNOWLEDGE_CHOICES,
  N,
  NODE_DETAILS,
} from './mockData';

/**
 * Scripted demo backend. Simulates a voice tutor so the UI can be shown with no server:
 * streaming captions, a pulsing orb, the map growing node by node, and a correction.
 * The script always tells the backpropagation story, whatever files are dropped.
 */

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

function kindOf(file: File): MaterialKind {
  if (file.type.startsWith('image/')) return 'image';
  if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) return 'pdf';
  if (file.type.startsWith('text/')) return 'text';
  return 'doc';
}

function labelOf(kind: MaterialKind): string {
  return { pdf: 'PDF', image: 'Image', doc: 'Document', text: 'Text' }[kind];
}

export function createMockBackend(): DysCoverBackend {
  const sessions = [...DEMO_SESSIONS];
  return {
    async createSession(files) {
      await wait(400);
      const materials: Material[] = files.length
        ? files.map((f, i) => ({ id: `m${i + 1}`, name: f.name, kind: kindOf(f), label: labelOf(kindOf(f)) }))
        : DEMO_MATERIALS;
      const session = { id: `new-${Date.now()}`, title: 'Backpropagation', topic: 'Neural networks', updatedAt: new Date().toISOString() };
      sessions.unshift(session);
      return { session, materials };
    },

    async listSessions() {
      await wait(150);
      return sessions;
    },

    async getSession(sessionId) {
      await wait(250);
      const session = sessions.find((s) => s.id === sessionId) ?? sessions[0];
      const nodes: MapNode[] =
        session.id === 's-backprop'
          ? FINISHED_MAP
          : [{ id: 'root', parentId: null, label: session.title, subtitle: session.topic, status: 'normal' }];
      return { session, materials: DEMO_MATERIALS, nodes };
    },

    async getNodeDetail(_sessionId, nodeId) {
      await wait(200);
      const d = NODE_DETAILS[nodeId] ?? {
        title: nodeId,
        breadcrumb: [],
        summary: 'No details yet for this node.',
        messages: [],
      };
      return { nodeId, ...d };
    },

    connect(sessionId, onEvent) {
      return new MockLive(sessionId, onEvent);
    },
  };
}

type Stage = 'intro' | 'waitingChoice' | 'teaching' | 'free' | 'ended';

class MockLive implements LiveConnection {
  private stage: Stage = 'intro';
  private closed = false;
  private talking: 'user' | 'assistant' | null = null;
  private levelTimer: number;
  private level = 0;
  private run = 0; // bumps on end/close to cancel running scripts
  private prevStage: Stage = 'free';

  constructor(
    sessionId: string,
    private emit: (e: ServerEvent) => void,
  ) {
    // Fake loudness so the orb "breathes" with speech.
    this.levelTimer = window.setInterval(() => {
      const target = this.talking ? 0.35 + Math.random() * 0.65 : 0.04;
      this.level += (target - this.level) * 0.45;
      this.emit({ type: 'voice.level', level: this.level });
    }, 80);

    if (sessionId.startsWith('s-') && DEMO_SESSIONS.some((s) => s.id === sessionId)) {
      this.stage = 'free';
      this.guard(async (id) => {
        await this.say(id, 'Welcome back. Want to pick up where we left off?');
      });
    } else {
      this.guard((id) => this.intro(id));
    }
  }

  send(event: ClientEvent) {
    if (this.closed) return;
    switch (event.type) {
      case 'session.end':
        this.prevStage = this.stage;
        this.stage = 'ended';
        this.run++;
        this.talking = null;
        this.emit({ type: 'voice.status', status: 'ended' });
        return;
      case 'session.resume':
        this.stage = this.prevStage === 'ended' ? 'free' : this.prevStage;
        this.emit({ type: 'voice.status', status: 'listening' });
        return;
      case 'user.choice':
        if (this.stage === 'waitingChoice') this.guard((id) => this.teach(id, event.choiceId));
        return;
      case 'user.text':
        if (this.stage === 'waitingChoice') this.guard((id) => this.teach(id, 'know', event.text));
        else if (this.stage === 'free') this.guard((id) => this.freeReply(id, event.text));
        return;
      case 'user.node_opened':
        if (this.stage === 'free') {
          const d = NODE_DETAILS[event.nodeId];
          if (d) this.guard((id) => this.say(id, d.summary));
        }
        return;
      case 'user.map_edit':
        return; // the UI already applied the edit optimistically
    }
  }

  close() {
    this.closed = true;
    this.run++;
    window.clearInterval(this.levelTimer);
  }

  // ---------- script ----------

  private async intro(id: number) {
    this.emit({ type: 'voice.status', status: 'connecting' });
    await this.pause(id, 500);
    this.emit({ type: 'map.reset', nodes: [{ ...N.root, subtitle: 'Your map grows from here as we talk' }] });
    await this.say(id, "I've read all your files. How much do you already know about backpropagation? Just tell me.");
    this.emit({ type: 'prompt.choices', choices: KNOWLEDGE_CHOICES });
    this.stage = 'waitingChoice';
  }

  private async teach(id: number, choiceId: string, typed?: string) {
    this.stage = 'teaching';
    this.emit({ type: 'prompt.clear' });
    this.emit({ type: 'map.update', nodeId: 'root', patch: { subtitle: N.root.subtitle } });

    if (choiceId === 'new') {
      await this.userSays(id, "I'm new to this — guide me from the start.", true);
      await this.say(id, 'No problem. Backprop answers one question: how much did each weight add to the error?');
      this.add(N.forward);
      await this.say(id, "First, the forward pass. Data flows through the network, and we keep each layer's output.");
      this.add(N.save);
      await this.pause(id, 400);
      this.add(N.loss);
      await this.say(id, 'Then a loss measures how wrong we were.');
      this.add(N.chain);
      this.add(N.update);
      await this.say(id, 'And the chain rule carries that error backwards. Quick check — in your own words, what does backprop do?');
      this.settle(['forward', 'save', 'loss']);
      await this.pause(id, 1200);
      await this.userSays(id, 'I think backprop is the step that updates the weights.');
    } else {
      if (typed) await this.userSays(id, typed, true);
      else {
        await this.userSays(id, 'I know a bit — let me explain first.', true);
        await this.say(id, "Go ahead, I'm listening.");
        await this.pause(id, 900);
        await this.userSays(id, 'You run the forward pass, get a loss, then use the chain rule… and I think backprop is the step that updates the weights.');
      }
      this.add(N.forward);
      this.add(N.loss);
      this.add(N.chain);
      this.add(N.update);
      await this.say(id, "Good — you've got the forward pass, the loss and the chain rule.");
      this.settle(['forward', 'loss']);
    }

    // The correction moment.
    this.emit({ type: 'voice.status', status: 'thinking' });
    await this.pause(id, 700);
    this.emit({
      type: 'map.update',
      nodeId: 'update',
      patch: {
        status: 'corrected',
        correction: { said: 'backprop updates weights', actually: 'Backprop finds gradients. The optimiser (SGD) updates weights.' },
      },
    });
    this.emit({ type: 'map.focus', nodeId: 'update' });
    await this.say(id, "Nearly! Backprop finds the gradients — the optimiser updates the weights. I've marked it in orange.");
    this.settle(['chain']);
    this.add(N.local);
    await this.pause(id, 300);
    this.add(N.back);
    this.emit({ type: 'map.focus', nodeId: 'back' });
    await this.say(id, 'One more idea: each layer passes its gradient back to the one before. Tap any bubble to see where it comes from in your slides.');
    this.settle(['local']);
    this.stage = 'free';
  }

  private async freeReply(id: number, text: string) {
    await this.userSays(id, text, true);
    await this.say(id, "Good question. In the real app I'd answer from your files here — and grow the map if it helps.");
  }

  // ---------- helpers ----------

  private add(node: MapNode) {
    this.emit({ type: 'map.add', node });
  }

  private settle(ids: string[]) {
    for (const nodeId of ids) this.emit({ type: 'map.update', nodeId, patch: { status: 'normal' } });
  }

  /** Assistant speaks: stream caption word by word. */
  private async say(id: number, text: string) {
    this.check(id);
    this.emit({ type: 'voice.status', status: 'speaking' });
    this.talking = 'assistant';
    await this.stream(id, 'assistant', text, 95);
    this.talking = null;
    this.emit({ type: 'voice.status', status: 'listening' });
    await this.pause(id, 350);
  }

  /** Simulated learner speech (stands in for the microphone in the demo). */
  private async userSays(id: number, text: string, instant = false) {
    this.check(id);
    this.emit({ type: 'voice.status', status: 'listening' });
    if (instant) {
      this.emit({ type: 'caption', caption: { role: 'user', text, final: true } });
    } else {
      this.talking = 'user';
      await this.stream(id, 'user', text, 170);
      this.talking = null;
    }
    this.emit({ type: 'voice.status', status: 'thinking' });
    await this.pause(id, 600);
  }

  private async stream(id: number, role: 'user' | 'assistant', text: string, msPerWord: number) {
    const words = text.split(' ');
    for (let i = 1; i <= words.length; i++) {
      this.check(id);
      this.emit({ type: 'caption', caption: { role, text: words.slice(0, i).join(' '), final: i === words.length } });
      await wait(msPerWord);
    }
  }

  private async pause(id: number, ms: number) {
    await wait(ms);
    this.check(id);
  }

  private check(id: number) {
    if (this.closed || id !== this.run) throw new Cancelled();
  }

  private guard(fn: (runId: number) => Promise<void>) {
    const id = ++this.run;
    fn(id).catch((e) => {
      if (!(e instanceof Cancelled)) console.error(e);
    });
  }
}

class Cancelled extends Error {}
