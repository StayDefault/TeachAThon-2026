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
  originalAvailable?: boolean;
}

// ---------- Concept map ----------

/**
 * normal    – ordinary node
 * new       – system-created (blue outline + "New" tag until opened)
 * corrected – the learner had a misconception here; shown in orange with "You said / Actually"
 */
export type NodeStatus = 'normal' | 'new' | 'corrected';

/**
 * How well the learner understands a concept (independent of status):
 * introduced – explained to the learner; shown paler until they show understanding
 * understood – the learner explained it correctly; shows their own words
 * review     – not yet understood after a couple of tries, or skipped; revisit later
 */
export type Mastery = 'introduced' | 'understood' | 'review';

export interface MapNode {
  id: string;
  parentId: string | null; // exactly one node has parentId === null (the root / thesis)
  label: string; // keep it SHORT (≤ ~5 words). Dyslexia-friendly: the voice explains, the map only hints.
  subtitle?: string; // optional one-liner, used on the root
  status: NodeStatus;
  correction?: {
    said: string; // what the learner said, quoted (never struck through)
    actually: string; // the correct idea, one short sentence
  } | null;
  hiddenChildren?: number; // > 0 shows a "+N" badge (children exist but are collapsed)
  order?: number; // sibling order; lower first
  position?: { x: number; y: number }; // learner-placed map position
  userEdited?: boolean;
  pendingRemoval?: string | null;
  planId?: string; // lesson concept this node represents
  mastery?: Mastery;
  learnerWords?: string; // the learner's own explanation, shown when understood
}

/** A labelled cross-link between two nodes in different branches. */
export interface MapEdge {
  id: string;
  from: string;
  to: string;
  label: string; // short relation, e.g. "causes"
}

// ---------- Lesson plan ----------

export type LessonState = 'unseen' | 'introduced' | 'attempted' | 'understood' | 'review' | 'skipped';

export interface LessonItem {
  id: string;
  title: string;
  state: LessonState;
}

export interface LessonProgress {
  items: LessonItem[];
  focusId: string | null; // the concept being studied now
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
  correction?: { said: string; actually: string };
  userEdited?: boolean;
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
  edges?: MapEdge[];
  lesson?: LessonProgress;
  messages?: ChatMessage[];
}

// ---------- Live voice session ----------

export type VoiceStatus = 'idle' | 'connecting' | 'listening' | 'thinking' | 'speaking' | 'ended';

export interface Caption {
  role: 'user' | 'assistant';
  text: string; // full text so far (not a delta)
  final: boolean; // false while still streaming
}

/** Events the backend pushes to the frontend over the live connection. */
export type ServerEvent =
  | { type: 'voice.audio'; sampleRate: number }
  | { type: 'voice.interrupt' }
  | { type: 'voice.status'; status: VoiceStatus }
  | { type: 'voice.level'; level: number } // 0..1, loudness of whoever is talking (drives the orb)
  | { type: 'caption'; caption: Caption; message?: ChatMessage }
  | { type: 'map.reset'; nodes: MapNode[] }
  | { type: 'map.add'; node: MapNode }
  | { type: 'map.update'; nodeId: string; patch: Partial<MapNode> }
  | { type: 'map.remove'; nodeId: string }
  | { type: 'map.focus'; nodeId: string } // briefly highlight / scroll to a node
  | { type: 'map.expanded'; nodeId: string } // show this branch's children and the expand/learn actions
  | { type: 'map.edges'; edges: MapEdge[] } // replace all cross-links
  | ({ type: 'lesson.update' } & LessonProgress)
  | { type: 'error'; message: string };

/** Events the frontend sends to the backend over the live connection. */
export type ClientEvent =
  | { type: 'user.text'; text: string } // typed message (text mode)
  | { type: 'user.node_opened'; nodeId: string } // selection context only; never starts speech or a tutor turn
  | { type: 'user.action'; action: 'learn' | 'expand'; nodeId?: string; planId?: string } // a button press the tutor handles like a request
  | { type: 'user.map_edit'; op: 'rename' | 'remove' | 'add' | 'move' | 'update' | 'acknowledge' | 'keep'; nodeId?: string; parentId?: string; label?: string; summary?: string; x?: number; y?: number }
  | { type: 'session.end' }
  | { type: 'session.resume' };
