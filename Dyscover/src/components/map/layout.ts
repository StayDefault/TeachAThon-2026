import type { MapNode } from '../../types';

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

const COL = 340; // column pitch
const GAP = 24; // vertical gap between sibling subtrees

function sizeOf(node: MapNode, depth: number): { w: number; h: number } {
  if (depth === 0) return { w: 250, h: 84 };
  if (node.status === 'corrected') return { w: 290, h: 156 };
  return { w: 250, h: depth === 1 ? 56 : 52 };
}

export function layoutTree(nodes: MapNode[]): Layout {
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
    for (const c of children) cursor = place(c, depth + 1, cursor) + GAP;
    const bottom = cursor - GAP;

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

  const bottom = place(root, 0, 0);

  const edges: Edge[] = [];
  for (const b of boxes.values()) {
    if (!b.node.parentId) continue;
    const p = boxes.get(b.node.parentId);
    if (!p) continue;
    const x1 = p.x + p.w;
    const y1 = p.y + p.h / 2;
    const x2 = b.x;
    const y2 = b.y + b.h / 2;
    const mx = x1 + (x2 - x1) / 2;
    const r = Math.min(10, Math.abs(y2 - y1) / 2);
    const dir = y2 > y1 ? 1 : -1;
    const d =
      Math.abs(y2 - y1) < 1
        ? `M${x1},${y1} H${x2}`
        : `M${x1},${y1} H${mx - r} Q${mx},${y1} ${mx},${y1 + dir * r} V${y2 - dir * r} Q${mx},${y2} ${mx + r},${y2} H${x2}`;
    edges.push({ id: b.node.id, d, tone: b.node.status });
  }

  const all = [...boxes.values()];
  return {
    boxes: all,
    edges,
    width: Math.max(...all.map((b) => b.x + b.w)),
    height: Math.max(bottom, ...all.map((b) => b.y + b.h)),
  };
}
