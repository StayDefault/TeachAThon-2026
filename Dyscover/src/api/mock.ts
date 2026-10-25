import type { ChatMessage, ClientEvent, LessonItem, LessonProgress, MapEdge, MapNode, Material, MaterialKind, NodeDetail, ServerEvent } from '../types';
import type { DysCoverBackend, LiveConnection } from './contract';
import {
  DEMO_MATERIALS,
  DEMO_SESSIONS,
  FINISHED_LESSON,
  FINISHED_MAP,
  FORWARD_WORDS,
  GRADIENT_LINK,
  LESSON,
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
  const originals = new Map<string, string>();
  const sessionMaterials = new Map<string, Material[]>();
  const sessionNodes = new Map<string, MapNode[]>();
  const editedDetails = new Map<string, NodeDetail>();
  const histories = new Map<string, ChatMessage[]>();
  const sessionEdges = new Map<string, MapEdge[]>([['s-backprop', [GRADIENT_LINK]]]);
  const sessionLessons = new Map<string, LessonProgress>([['s-backprop', FINISHED_LESSON]]);
  const initialNodes = (sessionId: string): MapNode[] => sessionId === 's-backprop'
    ? FINISHED_MAP.map((node) => ({ ...node }))
    : [{ id: 'root', parentId: null, label: sessions.find((item) => item.id === sessionId)?.title ?? 'Backpropagation',
         subtitle: sessions.find((item) => item.id === sessionId)?.topic, status: 'normal' }];
  return {
    async createSession(files) {
      await wait(400);
      const materials: Material[] = files.length
        ? files.map((f, i) => ({ id: `m${i + 1}`, name: f.name, kind: kindOf(f), label: labelOf(kindOf(f)), originalAvailable: true }))
        : DEMO_MATERIALS;
      const session = { id: `new-${Date.now()}`, title: 'Backpropagation', topic: 'Neural networks', updatedAt: new Date().toISOString() };
      sessions.unshift(session);
      sessionMaterials.set(session.id, materials);
      files.forEach((file, i) => originals.set(`${session.id}/m${i + 1}`, URL.createObjectURL(file)));
      return { session, materials };
    },

    async listSessions() {
      await wait(150);
      return sessions;
    },

    async getSession(sessionId) {
      await wait(250);
      const session = sessions.find((s) => s.id === sessionId);
      if (!session) throw new Error('Session not found.');
      const nodes = sessionNodes.get(sessionId) ?? initialNodes(sessionId);
      return { session, materials: sessionMaterials.get(sessionId) ?? DEMO_MATERIALS, nodes, edges: sessionEdges.get(sessionId) ?? [],
        lesson: sessionLessons.get(sessionId), messages: histories.get(sessionId) ?? [] };
    },

    materialUrl(sessionId, materialId) {
      return originals.get(`${sessionId}/${materialId}`) ?? '';
    },

    async deleteSession(sessionId) {
      const index = sessions.findIndex((session) => session.id === sessionId);
      if (index < 0) throw new Error('Session not found.');
      sessions.splice(index, 1);
      sessionMaterials.delete(sessionId);
      histories.delete(sessionId);
      for (const [key, value] of originals) if (key.startsWith(`${sessionId}/`)) {
        URL.revokeObjectURL(value);
        originals.delete(key);
      }
    },

    async getNodeDetail(sessionId, nodeId) {
      await wait(200);
      const edited = editedDetails.get(`${sessionId}/${nodeId}`);
      if (edited) return edited;
      const d = NODE_DETAILS[nodeId] ?? {
        title: nodeId,
        breadcrumb: [],
        summary: 'No details yet for this node.',
        messages: [],
      };
      const { messages: _messages, ...detail } = d;
      return { nodeId, ...detail };
    },

    async getHistory(sessionId) {
      return histories.get(sessionId) ?? [];
    },

    connect(sessionId, onEvent) {
      if (!sessionNodes.has(sessionId)) sessionNodes.set(sessionId, initialNodes(sessionId));
      if (!histories.has(sessionId)) {
        const previous = sessionId.startsWith('s-') ? Object.values(NODE_DETAILS).flatMap(detail => detail.messages) : [];
        histories.set(sessionId, [...new Map(previous.map(item => [item.id, item])).values()].sort((a, b) => a.at.localeCompare(b.at)));
      }
      const emit = (event: ServerEvent) => {
        if (event.type === 'caption' && event.caption.final) {
          const message = { id: crypto.randomUUID(), role: event.caption.role, text: event.caption.text, at: new Date().toISOString() };
          histories.get(sessionId)?.push(message);
          event = { ...event, message };
        }
        const nodes = sessionNodes.get(sessionId) ?? [];
        if (event.type === 'map.reset') sessionNodes.set(sessionId, event.nodes);
        if (event.type === 'map.edges') sessionEdges.set(sessionId, event.edges);
        if (event.type === 'lesson.update') sessionLessons.set(sessionId, { items: event.items, focusId: event.focusId });
        if (event.type === 'map.add') sessionNodes.set(sessionId, [...nodes.filter((node) => node.id !== event.node.id), event.node]);
        if (event.type === 'map.update') sessionNodes.set(sessionId, nodes.map((node) => node.id === event.nodeId ? { ...node, ...event.patch } : node));
        if (event.type === 'map.remove') {
          const removed = new Set([event.nodeId]);
          for (let changed = true; changed;) {
            changed = false;
            for (const node of nodes) if (node.parentId && removed.has(node.parentId) && !removed.has(node.id)) {
              removed.add(node.id);
              changed = true;
            }
          }
          sessionNodes.set(sessionId, nodes.filter((node) => !removed.has(node.id)));
          for (const id of removed) editedDetails.delete(`${sessionId}/${id}`);
        }
        onEvent(event);
      };
      const edit = (event: Extract<ClientEvent, { type: 'user.map_edit' }>) => {
        const nodes = sessionNodes.get(sessionId) ?? [];
        const node = nodes.find((item) => item.id === event.nodeId);
        if (event.op === 'add' && event.nodeId && event.parentId && event.label) {
          emit({ type: 'map.add', node: { id: event.nodeId, parentId: event.parentId, label: event.label, status: 'normal', userEdited: true, order: nodes.filter((item) => item.parentId === event.parentId).length } });
          editedDetails.set(`${sessionId}/${event.nodeId}`, { nodeId: event.nodeId, title: event.label, breadcrumb: [], summary: event.label, userEdited: true });
        } else if (event.op === 'acknowledge' && node) {
          if (node.status === 'new') emit({ type: 'map.update', nodeId: node.id, patch: { status: 'normal' } });
        } else if (event.op === 'keep' && node) {
          emit({ type: 'map.update', nodeId: node.id, patch: { pendingRemoval: null } });
        } else if (event.op === 'remove' && node) {
          emit({ type: 'map.remove', nodeId: node.id });
        } else if (event.op === 'move' && node && event.x !== undefined && event.y !== undefined) {
          emit({ type: 'map.update', nodeId: node.id, patch: { position: { x: event.x, y: event.y } } });
        } else if (event.op === 'update' && node && event.label && event.summary) {
          emit({ type: 'map.update', nodeId: node.id, patch: { label: event.label, userEdited: true, status: 'normal', correction: null, pendingRemoval: null } });
          const previous = editedDetails.get(`${sessionId}/${node.id}`) ?? NODE_DETAILS[node.id];
          editedDetails.set(`${sessionId}/${node.id}`, { nodeId: node.id, ...previous, title: event.label, summary: event.summary, userEdited: true });
        }
      };
      return new MockLive(sessionId, emit, edit);
    },
  };
}

type Stage = 'intro' | 'teaching' | 'free' | 'ended';

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
    private edit: (e: Extract<ClientEvent, { type: 'user.map_edit' }>) => void,
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
      case 'user.text':
        if (this.stage !== 'ended') {
          this.stage = 'free';
          this.guard((id) => this.freeReply(id, event.text));
        }
        return;
      case 'user.action':
        if (this.stage !== 'ended') {
          this.stage = 'free';
          const title = LESSON.find((item) => item.id === event.planId)?.title ?? event.nodeId ?? 'this topic';
          this.guard((id) => this.freeReply(id, event.action === 'expand' ? `Expand ${title} into its subtopics.` : `Teach me about ${title}.`));
        }
        return;
      case 'user.node_opened':
        return;
      case 'user.map_edit':
        this.edit(event);
        return;
    }
  }

  setInputMode(_mode: 'voice' | 'text') {
    // The scripted demo has no microphone stream.
  }

  close() {
    this.closed = true;
    this.run++;
    window.clearInterval(this.levelTimer);
  }

  // ---------- script ----------

  private async intro(id: number) {
    this.emit({ type: 'voice.status', status: 'connecting' });
    this.emit({ type: 'map.reset', nodes: [{ ...N.root, status: 'new', subtitle: 'Your map grows from here as we talk' }] });
    this.emit({ type: 'map.edges', edges: [] });
    this.progress({}, 'p1');
    await this.pause(id, 500);
    this.stage = 'teaching';
    await this.say(id, "I've read all your files. We'll go through four ideas, one at a time. First, the forward pass.");
    await this.teach(id);
  }

  private lesson: LessonItem[] = LESSON;

  private progress(states: Record<string, LessonItem['state']>, focusId: string) {
    this.lesson = this.lesson.map((item) => (states[item.id] ? { ...item, state: states[item.id] } : item));
    this.emit({ type: 'lesson.update', items: this.lesson, focusId });
  }

  private async teach(id: number) {
    this.stage = 'teaching';
    this.emit({ type: 'map.update', nodeId: 'root', patch: { subtitle: N.root.subtitle } });

    this.add(N.forward);
    this.progress({ p1: 'introduced' }, 'p1');
    await this.say(id, "Data flows through the network one layer at a time, and we keep each layer's output for later.");
    this.add(N.save);
    await this.say(id, 'Try saying it back in your own words. What happens in the forward pass?');
    await this.pause(id, 1000);
    await this.userSays(id, `I think ${FORWARD_WORDS}.`);

    // Understood: the node fills in with the learner's own words, and the lesson moves on.
    this.emit({ type: 'map.update', nodeId: 'forward', patch: { mastery: 'understood', learnerWords: FORWARD_WORDS } });
    this.emit({ type: 'map.focus', nodeId: 'forward' });
    this.add(N.loss);
    this.progress({ p1: 'understood', p2: 'introduced' }, 'p2');
    await this.say(id, "Exactly, that's it. Next, the loss: one number that says how wrong the prediction was.");
    this.add(N.chain);
    this.progress({ p3: 'introduced' }, 'p3');
    await this.say(id, 'Then the chain rule carries that error backwards, layer by layer. Quick check: what does backprop do?');
    await this.pause(id, 1200);
    await this.userSays(id, 'I think backprop is the step that updates the weights.');

    // A misconception: corrected on the map, explained a different way.
    this.emit({ type: 'voice.status', status: 'thinking' });
    await this.pause(id, 700);
    this.add({
      ...N.update,
      status: 'corrected',
      correction: { said: 'backprop is the step that updates the weights', actually: 'Backprop finds gradients. The optimiser (SGD) updates weights.' },
    });
    this.progress({ p4: 'attempted' }, 'p4');
    this.emit({ type: 'map.focus', nodeId: 'update' });
    await this.say(id, "Close. Think of backprop as the satnav that finds the direction, and the optimiser as the driver who moves. I've marked it in orange.");
    this.add(N.local);
    await this.pause(id, 300);
    this.add(N.back);
    this.emit({ type: 'map.edges', edges: [GRADIENT_LINK] });
    this.emit({ type: 'map.focus', nodeId: 'back' });
    await this.say(id, 'Each layer passes its gradient back, and those gradients feed the weight update. Tap any bubble to see where it comes from.');
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
