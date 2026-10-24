import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { MapNode } from '../../types';
import { IconArrange, IconFit, IconMinus, IconPencil, IconPlus } from '../Icons';
import { layoutTree, type Box } from './layout';
import './ConceptMap.css';

/**
 * The concept map. Data in (nodes), clicks out (onOpen).
 * Existing positions stay put as new nodes are added; new nodes slide in.
 */
export function ConceptMap({
  nodes,
  focusId,
  selectedId,
  onOpen,
  onMove,
  onFocusDone,
}: {
  nodes: MapNode[];
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
  const viewport = useRef<HTMLDivElement>(null);
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
      {!seed && <Legend />}
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

      <div className={`map ${selectedId ? 'map--dimmed' : ''}`} ref={viewport}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          const nodeId = event.dataTransfer.getData('text/dyscover-node');
          const stage = viewport.current?.querySelector('.map__stage');
          const node = nodes.find((item) => item.id === nodeId);
          if (!stage || !node || nodeId === 'root') return;
          const rect = stage.getBoundingClientRect();
          onMove(nodeId, Math.max(0, Math.round((event.clientX - rect.left) / scale - 125)), Math.max(0, Math.round((event.clientY - rect.top) / scale - 28)));
        }}>
        <div className="map__sizer" style={{ width: layout.width * scale, height: layout.height * scale }}>
          <div className="map__stage" style={{ width: layout.width, height: layout.height, transform: `scale(${scale})` }}>
            <svg className="map__edges" width={layout.width} height={layout.height} aria-hidden="true">
              {layout.edges.map((e) => (
                <path key={e.id} d={e.d} className={`map__edge map__edge--${e.tone}`} />
              ))}
            </svg>
            {layout.boxes.map((b) => (
              <NodeBox
                key={b.node.id}
                box={b}
                seed={seed}
                focused={focusId === b.node.id}
                selected={selectedId === b.node.id}
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

function NodeBox({ box, seed, focused, selected, onOpen, onMove }: { box: Box; seed: boolean; focused: boolean; selected: boolean; onOpen: (id: string) => void; onMove: (id: string, x: number, y: number) => void }) {
  const { node, depth } = box;
  const cls = [
    'node',
    depth === 0 ? 'node--root' : depth === 1 ? 'node--l1' : 'node--l2',
    `node--${node.status}`,
    node.userEdited && node.status !== 'corrected' && !node.pendingRemoval ? 'node--edited' : '',
    node.pendingRemoval ? 'node--removal' : '',
    seed && node.status === 'new' ? 'node--seed' : '',
    focused ? 'node--focus' : '',
    selected ? 'node--selected' : '',
  ].join(' ');

  return (
    <button
      data-node={node.id}
      draggable={!seed && node.id !== 'root'}
      onDragStart={(event) => event.dataTransfer.setData('text/dyscover-node', node.id)}
      className={cls}
      style={{ left: box.x, top: box.y, width: box.w, minHeight: box.h }}
      onClick={() => onOpen(node.id)}
      onKeyDown={(event) => {
        if (!event.altKey || node.id === 'root') return;
        const offset = { ArrowLeft: [-20, 0], ArrowRight: [20, 0], ArrowUp: [0, -20], ArrowDown: [0, 20] }[event.key];
        if (!offset) return;
        event.preventDefault();
        onMove(node.id, Math.max(0, box.x + offset[0]), Math.max(0, box.y + offset[1]));
      }}
      aria-label={`${node.label}${node.pendingRemoval ? ' (proposed removal)' : node.status === 'corrected' ? ' (corrected)' : node.userEdited ? ' (edited)' : node.status === 'new' ? ' (new)' : ''}${node.id !== 'root' ? '. Drag or use Alt and arrow keys to move' : ''}`}
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
          </span>
          {node.pendingRemoval ? <span className="node__removal">Review removal</span>
            : node.userEdited ? <span className="node__edited">Edited</span>
              : node.status === 'new' && <span className="node__new">New</span>}
          {!!node.hiddenChildren && <span className="node__more">+{node.hiddenChildren}</span>}
        </>
      )}
    </button>
  );
}

function Legend() {
  return (
    <div className="legend" aria-label="Node colors">
      <span>
        <i className="legend__swatch legend__swatch--normal" /> Default
      </span>
      <span>
        <i className="legend__swatch legend__swatch--new" /> New
      </span>
      <span>
        <i className="legend__swatch legend__swatch--edited" /> Edited
      </span>
      <span><i className="legend__swatch legend__swatch--fix" /> Corrected</span>
      <span><i className="legend__swatch legend__swatch--removal" /> Proposed removal</span>
    </div>
  );
}
