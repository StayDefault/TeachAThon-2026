/**
 * Shared data model between the DysCover frontend and backend.
 * Every shape here is mirrored in docs/API.md — keep the two in sync.
 */

// ---------- Materials ----------

export type MaterialKind = 'pdf' | 'image' | 'doc' | 'text';

export interface Material {
  id: string;
  name: string; // file name, e.g. "Lecture3_Backprop.pdf"
  kind: MaterialKind;
  label: string; // short human label, e.g. "Lecture slides"
}

// ---------- Concept map ----------

/**
 * normal    – ordinary node
 * new       – just added from the conversation (blue outline + "New" tag; clear it after a while)
 * corrected – the learner had a misconception here; shown in orange with "You said / Actually"
 */
export type NodeStatus = 'normal' | 'new' | 'corrected';

export interface MapNode {
  id: string;
  parentId: string | null; // exactly one node has parentId === null (the root / thesis)
  label: string; // keep it SHORT (≤ ~5 words). Dyslexia-friendly: the voice explains, the map only hints.
  subtitle?: string; // optional one-liner, used on the root
  status: NodeStatus;
  correction?: {
    said: string; // what the learner said, shown struck through
    actually: string; // the correct idea, one short sentence
  };
  hiddenChildren?: number; // > 0 shows a "+N" badge (children exist but are collapsed)
  order?: number; // sibling order; lower first
}

// ---------- Node detail (the quarter-screen panel) ----------

export interface SourceRef {
  materialId: string;
  fileName: string;
  page?: number; // slide or page number, 1-based
  quote: string; // the exact sentence from the source to highlight
  context?: string; // optional heading of the slide/page
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  audioUrl?: string; // optional: replayable audio for assistant messages
  at: string; // ISO timestamp
}

export interface NodeDetail {
  nodeId: string;
  title: string;
  breadcrumb: string[]; // e.g. ["Backpropagation"]
  source?: SourceRef;
  summary: string; // 1–2 plain-language sentences
  messages: ChatMessage[]; // conversation about this node
}

// ---------- Sessions ----------

export interface SessionSummary {
  id: string;
  title: string; // e.g. "Backpropagation"
  topic: string; // grouping label, e.g. "Neural networks"
  updatedAt: string; // ISO timestamp
  durationMin?: number;
}

export interface SessionSnapshot {
  session: SessionSummary;
  materials: Material[];
  nodes: MapNode[];
}

// ---------- Live voice session ----------

export type VoiceStatus = 'idle' | 'connecting' | 'listening' | 'thinking' | 'speaking' | 'ended';

export interface Caption {
  role: 'user' | 'assistant';
  text: string; // full text so far (not a delta)
  final: boolean; // false while still streaming
}

export interface Choice {
  id: string;
  title: string;
  subtitle?: string;
}

/** Events the backend pushes to the frontend over the live connection. */
export type ServerEvent =
  | { type: 'voice.status'; status: VoiceStatus }
  | { type: 'voice.level'; level: number } // 0..1, loudness of whoever is talking (drives the orb)
  | { type: 'caption'; caption: Caption }
  | { type: 'prompt.choices'; choices: Choice[] } // quick-reply buttons (e.g. "How much do you know?")
  | { type: 'prompt.clear' }
  | { type: 'map.reset'; nodes: MapNode[] }
  | { type: 'map.add'; node: MapNode }
  | { type: 'map.update'; nodeId: string; patch: Partial<MapNode> }
  | { type: 'map.remove'; nodeId: string }
  | { type: 'map.focus'; nodeId: string } // briefly highlight / scroll to a node
  | { type: 'error'; message: string };

/** Events the frontend sends to the backend over the live connection. */
export type ClientEvent =
  | { type: 'user.text'; text: string } // typed message (text mode)
  | { type: 'user.choice'; choiceId: string }
  | { type: 'user.node_opened'; nodeId: string } // learner opened a node; the model may talk about it
  | { type: 'user.map_edit'; op: 'rename' | 'remove' | 'add'; nodeId?: string; parentId?: string; label?: string }
  | { type: 'session.end' }
  | { type: 'session.resume' };
