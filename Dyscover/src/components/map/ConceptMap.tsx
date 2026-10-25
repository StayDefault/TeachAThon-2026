import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { MapEdge, MapNode } from '../../types';
import { IconArrange, IconFit, IconMinus, IconPencil, IconPlus } from '../Icons';
import { crossLinks, layoutTree, type Box } from './layout';
import './ConceptMap.css';

/**
 * The concept map. Data in (nodes), clicks out (onOpen).
 * Existing positions stay put as new nodes are added; new nodes slide in.
 */
export function ConceptMap({
  nodes,
  edges = [],
  focusId,
  selectedId,
  onOpen,
  onMove,
  onFocusDone,
}: {
  nodes: MapNode[];
  edges?: MapEdge[];
  focusId: string | null;
  selectedId: string | null;
  onOpen: (nodeId: string) => void;
  onMove: (nodeId: string, x: number, y: number) => void;
  onFocusDone: () => void;
}) {
  const previousLayout = useRef<ReturnType<typeof layoutTree> | null>(null);
  const [arrangement, setArrangement] = useState(0);
  const layout = useMemo(() => {
    const next = layoutTree(nodes, previousLayout.current ?? undefined);
    previousLayout.current = next;
    return next;
  }, [nodes, arrangement]);
  const links = useMemo(() => crossLinks(layout.boxes, edges), [layout, edges]);
  const viewport = useRef<HTMLDivElement>(null);
  const pan = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  const [panning, setPanning] = useState(false);
  const [scale, setScale] = useState(1);
  const [autoFit, setAutoFit] = useState(true);
  const seed = nodes.length <= 1;

  const fit = useCallback(() => {
    const el = viewport.current;
    if (!el || !layout.width) return;
    const s = Math.min(1, (el.clientWidth - 48) / layout.width, (el.clientHeight - 24) / layout.height);
    setScale(Math.max(0.4, s));
  }, [layout.width, layout.height]);

  useLayoutEffect(() => {
    if (arrangement > 0 || nodes.length <= 1) fit();
  }, [arrangement]);

  useLayoutEffect(() => {
    if (autoFit && nodes.length <= 1) fit();
  }, [autoFit, fit, nodes.length]);

  useEffect(() => {
    if (!autoFit) return;
    window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
  }, [autoFit, fit]);

  // Scroll a focused node into view, then clear the focus after the pulse.
  useEffect(() => {
    if (!focusId) return;
    const el = viewport.current?.querySelector(`[data-node="${CSS.escape(focusId)}"]`);
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
    const t = setTimeout(onFocusDone, 2400);
    return () => clearTimeout(t);
  }, [focusId, onFocusDone]);

  const zoom = (f: number) => {
    setAutoFit(false);
    setScale((s) => Math.min(1.6, Math.max(0.4, s * f)));
  };

  return (
    <>
      {!seed && <Legend nodes={nodes} />}
      {!seed && (
        <div className="map-tools" role="toolbar" aria-label="Map tools">
          <button className="icon-btn" aria-label="Arrange branches" title="Arrange branches" onClick={() => { previousLayout.current = null; setArrangement((value) => value + 1); }}>
            <IconArrange />
          </button>
          <button className="icon-btn" onClick={() => zoom(1.15)} aria-label="Zoom in">
            <IconPlus />
          </button>
          <button className="icon-btn" onClick={() => zoom(1 / 1.15)} aria-label="Zoom out">
            <IconMinus />
          </button>
          <button
            className="icon-btn"
            onClick={() => {
              setAutoFit(true);
              fit();
            }}
            aria-label="Fit map to screen"
          >
            <IconFit />
          </button>
        </div>
      )}

      <div className={`map ${selectedId ? 'map--dimmed' : ''} ${panning ? 'map--panning' : ''}`} ref={viewport}
        onPointerDown={(event) => {
          // Mouse users drag the background to pan; touch already scrolls natively.
          const el = viewport.current;
          if (!el || event.pointerType !== 'mouse' || event.button !== 0 || (event.target as HTMLElement).closest('.node')) return;
          pan.current = { x: event.clientX, y: event.clientY, left: el.scrollLeft, top: el.scrollTop };
          el.setPointerCapture(event.pointerId);
          setPanning(true);
        }}
        onPointerMove={(event) => {
          const el = viewport.current;
          if (!el || !pan.current) return;
          el.scrollLeft = pan.current.left - (event.clientX - pan.current.x);
          el.scrollTop = pan.current.top - (event.clientY - pan.current.y);
        }}
        onPointerUp={() => { pan.current = null; setPanning(false); }}
        onPointerCancel={() => { pan.current = null; setPanning(false); }}>
        <div className="map__sizer" style={{ width: layout.width * scale, height: layout.height * scale }}>
          <div className="map__stage" style={{ width: layout.width, height: layout.height, transform: `scale(${scale})` }}>
            <svg className="map__edges" width={layout.width} height={layout.height} aria-hidden="true">
              {layout.edges.map((e) => (
                <path key={e.id} d={e.d} className={`map__edge map__edge--${e.tone}`} />
              ))}
              {links.map((link) => <path key={link.id} d={link.d} className="map__link" />)}
            </svg>
            {links.map((link) => (
              <span key={link.id} className="map__link-label" style={{ left: link.x, top: link.y }}>{link.label}</span>
            ))}
            {layout.boxes.map((b) => (
              <NodeBox
                key={b.node.id}
                box={b}
                seed={seed}
                focused={focusId === b.node.id}
                selected={selectedId === b.node.id}
                scale={scale}
                onOpen={onOpen}
                onMove={onMove}
              />
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

function NodeBox({ box, seed, focused, selected, scale, onOpen, onMove }: { box: Box; seed: boolean; focused: boolean; selected: boolean; scale: number; onOpen: (id: string) => void; onMove: (id: string, x: number, y: number) => void }) {
  const { node, depth } = box;
  const movable = !seed && node.id !== 'root';
  const drag = useRef<{ x: number; y: number; dx: number; dy: number; moved: boolean } | null>(null);
  const dragged = useRef(false);
  const [offset, setOffset] = useState<[number, number] | null>(null);
  const tag = node.pendingRemoval ? <span className="node__removal">Review removal</span>
    : node.userEdited ? <span className="node__edited">Edited</span>
      : node.status === 'new' ? <span className="node__new">New</span>
        : node.mastery === 'review' ? <span className="node__review">Review</span>
          : node.mastery === 'understood' ? <span className="node__check" aria-hidden="true">✓</span> : null;
  const cls = [
    'node',
    depth === 0 ? 'node--root' : depth === 1 ? 'node--l1' : 'node--l2',
    `node--${node.status}`,
    node.mastery && node.mastery !== 'introduced' ? `node--${node.mastery}` : '',
    node.userEdited && node.status !== 'corrected' && !node.pendingRemoval ? 'node--edited' : '',
    node.pendingRemoval ? 'node--removal' : '',
    seed && node.status === 'new' ? 'node--seed' : '',
    focused ? 'node--focus' : '',
    selected ? 'node--selected' : '',
    movable ? 'node--movable' : '',
    offset ? 'node--dragging' : '',
  ].join(' ');
  const state = node.pendingRemoval ? ' (proposed removal)' : node.status === 'corrected' ? ' (corrected)' : node.userEdited ? ' (edited)'
    : node.status === 'new' ? ' (new)' : node.mastery === 'understood' ? ' (understood)' : node.mastery === 'review' ? ' (to review)' : '';

  return (
    <button
      data-node={node.id}
      className={cls}
      style={{ left: box.x, top: box.y, width: box.w, minHeight: box.h, transform: offset ? `translate(${offset[0]}px, ${offset[1]}px)` : undefined }}
      onPointerDown={(event) => {
        if (!movable || event.button !== 0) return;
        drag.current = { x: event.clientX, y: event.clientY, dx: 0, dy: 0, moved: false };
        event.currentTarget.setPointerCapture(event.pointerId);
      }}
      onPointerMove={(event) => {
        const d = drag.current;
        if (!d) return;
        d.dx = (event.clientX - d.x) / scale;
        d.dy = (event.clientY - d.y) / scale;
        if (!d.moved && Math.hypot(d.dx, d.dy) < 4) return;
        d.moved = true;
        setOffset([d.dx, d.dy]);
      }}
      onPointerUp={() => {
        const d = drag.current;
        drag.current = null;
        setOffset(null);
        if (!d?.moved) return;
        dragged.current = true;
        onMove(node.id, Math.max(0, Math.round(box.x + d.dx)), Math.max(0, Math.round(box.y + d.dy)));
      }}
      onPointerCancel={() => { drag.current = null; setOffset(null); }}
      onClick={() => {
        if (dragged.current) { dragged.current = false; return; }
        onOpen(node.id);
      }}
      onKeyDown={(event) => {
        if (!event.altKey || node.id === 'root') return;
        const step = { ArrowLeft: [-20, 0], ArrowRight: [20, 0], ArrowUp: [0, -20], ArrowDown: [0, 20] }[event.key];
        if (!step) return;
        event.preventDefault();
        onMove(node.id, Math.max(0, box.x + step[0]), Math.max(0, box.y + step[1]));
      }}
      aria-label={`${node.label}${state}${node.id !== 'root' ? '. Drag or use Alt and arrow keys to move' : ''}`}
    >
      {node.status === 'corrected' && node.correction && !node.pendingRemoval ? (
        <>
          <span className="node__badge">
            <IconPencil size={14} />
            CORRECTED
          </span>
          <span className="node__label">{node.label}</span>
          <span className="node__said">
            You said: “{node.correction.said}”
          </span>
          <span className="node__actually">{node.correction.actually}</span>
        </>
      ) : (
        <>
          <span className="node__text">
            <span className="node__label">{node.label}</span>
            {node.subtitle && <span className="node__sub">{node.subtitle}</span>}
            {node.mastery === 'understood' && node.learnerWords && <span className="node__words">“{node.learnerWords}”</span>}
          </span>
          {tag}
          {!!node.hiddenChildren && <span className="node__more">+{node.hiddenChildren}</span>}
        </>
      )}
    </button>
  );
}

const LEGEND: [string, string, (node: MapNode) => boolean][] = [
  ['normal', 'Explained', () => true],
  ['understood', 'Understood', (node) => node.mastery === 'understood'],
  ['review', 'Review later', (node) => node.mastery === 'review'],
  ['new', 'New', (node) => node.status === 'new'],
  ['fix', 'Corrected', (node) => node.status === 'corrected'],
  ['edited', 'Edited', (node) => !!node.userEdited],
  ['removal', 'Proposed removal', (node) => !!node.pendingRemoval],
];

/** Only the states currently on the map, so the key stays short. */
function Legend({ nodes }: { nodes: MapNode[] }) {
  return (
    <div className="legend" aria-label="Node colors">
      {LEGEND.filter(([, , present]) => nodes.some((node) => node.id !== 'root' && present(node))).map(([kind, label]) => (
        <span key={kind}><i className={`legend__swatch legend__swatch--${kind}`} /> {label}</span>
      ))}
    </div>
  );
}
