import type { MapEdge, MapNode } from '../../types';

/**
 * Left-to-right tidy tree layout. Pure function: nodes in → boxes + edges out.
 * Parents are vertically centred on their children; columns are fixed width.
 */

export interface Box {
  node: MapNode;
  depth: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Edge {
  id: string;
  d: string; // SVG path
  tone: 'normal' | 'new' | 'corrected';
}

export interface Layout {
  boxes: Box[];
  edges: Edge[];
  width: number;
  height: number;
}

const COL = 380;
const GAP = 28;
const BRANCH_GAP = 60;

function sizeOf(node: MapNode, depth: number): { w: number; h: number } {
  if (depth === 0) return { w: 250, h: 84 };
  if (node.status === 'corrected') return { w: 290, h: 156 };
  if (node.mastery === 'understood' && node.learnerWords) return { w: 250, h: 100 };
  return { w: 250, h: 64 };
}

export function layoutTree(nodes: MapNode[], previous?: Layout): Layout {
  const root = nodes.find((n) => n.parentId === null);
  if (!root) return { boxes: [], edges: [], width: 0, height: 0 };

  const kids = new Map<string, MapNode[]>();
  for (const n of nodes) {
    if (!n.parentId) continue;
    if (!kids.has(n.parentId)) kids.set(n.parentId, []);
    kids.get(n.parentId)!.push(n);
  }
  for (const list of kids.values()) list.sort((a, b) => (a.order ?? 0) - (b.order ?? 0));

  const boxes = new Map<string, Box>();

  const shift = (id: string, dy: number) => {
    const b = boxes.get(id)!;
    b.y += dy;
    for (const c of kids.get(id) ?? []) shift(c.id, dy);
  };

  // Returns the bottom edge of the placed subtree.
  const place = (node: MapNode, depth: number, top: number): number => {
    const { w, h } = sizeOf(node, depth);
    const box: Box = { node, depth, x: depth * COL, y: top, w, h };
    boxes.set(node.id, box);
    const children = kids.get(node.id) ?? [];
    if (children.length === 0) return top + h;

    let cursor = top;
    const gap = depth === 0 ? BRANCH_GAP : GAP;
    for (const c of children) cursor = place(c, depth + 1, cursor) + gap;
    const bottom = cursor - gap;

    const first = boxes.get(children[0].id)!;
    const last = boxes.get(children[children.length - 1].id)!;
    const center = (first.y + first.h / 2 + last.y + last.h / 2) / 2;
    box.y = center - h / 2;
    if (box.y < top) {
      const dy = top - box.y;
      shift(node.id, dy);
      return bottom + dy;
    }
    return Math.max(bottom, box.y + h);
  };

  const previousBoxes = new Map(previous?.boxes.map((box) => [box.node.id, box]));
  const stable = !!previous?.boxes.length && previous.boxes.every((box) => nodes.some((node) => node.id === box.node.id && node.parentId === box.node.parentId && node.order === box.node.order));
  let bottom: number;
  if (stable) {
    for (const node of nodes) {
      const before = previousBoxes.get(node.id);
      if (before) boxes.set(node.id, { ...before, node, ...sizeOf(node, before.depth) });
    }
    const columns = new Map<number, Box[]>();
    for (const box of boxes.values()) {
      const column = columns.get(box.depth) ?? [];
      column.push(box);
      columns.set(box.depth, column);
    }
    for (const column of columns.values()) {
      column.sort((a, b) => a.y - b.y);
      for (let i = 1; i < column.length; i++) {
        column[i].y = Math.max(column[i].y, column[i - 1].y + column[i - 1].h + GAP);
      }
    }
    const pending = nodes.filter((node) => !boxes.has(node.id));
    while (pending.length) {
      const index = pending.findIndex((node) => node.parentId && boxes.has(node.parentId));
      if (index < 0) break;
      const node = pending.splice(index, 1)[0];
      const parent = boxes.get(node.parentId!)!;
      const depth = parent.depth + 1;
      const { w, h } = sizeOf(node, depth);
      let y = Math.max(0, parent.y + (parent.h - h) / 2);
      const siblings = [...boxes.values()].filter((box) => box.node.parentId === node.parentId);
      if (siblings.length) y = Math.max(y, ...siblings.map((box) => box.y + box.h + GAP));
      let collision = true;
      while (collision) {
        collision = false;
        for (const box of boxes.values()) if (box.depth === depth && y < box.y + box.h + GAP && y + h + GAP > box.y) {
          y = box.y + box.h + GAP;
          collision = true;
        }
      }
      boxes.set(node.id, { node, depth, x: depth * COL, y, w, h });
    }
    bottom = Math.max(...[...boxes.values()].map((box) => box.y + box.h));
  } else {
    bottom = place(root, 0, 0);
  }

  for (const box of boxes.values()) if (box.node.position) {
    box.x = box.node.position.x;
    box.y = box.node.position.y;
  }
  const all = [...boxes.values()];
  return {
    boxes: all,
    edges: treeEdges(all),
    width: Math.max(...all.map((b) => b.x + b.w)),
    height: Math.max(bottom, ...all.map((b) => b.y + b.h)),
  };
}

/** Curved parent → child connectors. */
export function treeEdges(boxes: Box[]): Edge[] {
  const byId = new Map(boxes.map((box) => [box.node.id, box]));
  const edges: Edge[] = [];
  for (const b of boxes) {
    const p = b.node.parentId ? byId.get(b.node.parentId) : undefined;
    if (!p) continue;
    const x1 = p.x + p.w;
    const y1 = p.y + p.h / 2;
    const x2 = b.x;
    const y2 = b.y + b.h / 2;
    const bend = Math.max(36, Math.abs(x2 - x1) * 0.45);
    edges.push({ id: b.node.id, d: `M${x1},${y1} C${x1 + bend},${y1} ${x2 - bend},${y2} ${x2},${y2}`, tone: b.node.status });
  }
  return edges;
}

export interface CrossLink {
  id: string;
  d: string; // SVG path
  label: string;
  x: number; // label centre
  y: number;
}

/** Curved cross-links between boxes, bowed sideways so they don't run along tree edges. */
export function crossLinks(boxes: Box[], edges: MapEdge[]): CrossLink[] {
  const byId = new Map(boxes.map((box) => [box.node.id, box]));
  const links: CrossLink[] = [];
  for (const edge of edges) {
    const a = byId.get(edge.from);
    const b = byId.get(edge.to);
    if (!a || !b) continue;
    const down = b.y + b.h / 2 >= a.y + a.h / 2;
    const x1 = a.x + a.w / 2;
    const y1 = down ? a.y + a.h : a.y;
    const x2 = b.x + b.w / 2;
    const y2 = down ? b.y : b.y + b.h;
    const cx = (x1 + x2) / 2 + Math.max(60, Math.abs(y2 - y1) * 0.25);
    const cy = (y1 + y2) / 2;
    links.push({ id: edge.id, d: `M${x1},${y1} Q${cx},${cy} ${x2},${y2}`, label: edge.label,
      x: 0.25 * x1 + 0.5 * cx + 0.25 * x2, y: 0.25 * y1 + 0.5 * cy + 0.25 * y2 });
  }
  return links;
}
