import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { MapNode } from '../../types';
import { IconFit, IconMinus, IconPencil, IconPlus } from '../Icons';
import { layoutTree, type Box } from './layout';
import './ConceptMap.css';

/**
 * The concept map. Data in (nodes), clicks out (onOpen).
 * Positions animate when the tree re-lays out; new nodes slide in.
 */
export function ConceptMap({
  nodes,
  focusId,
  selectedId,
  onOpen,
  onFocusDone,
}: {
  nodes: MapNode[];
  focusId: string | null;
  selectedId: string | null;
  onOpen: (nodeId: string) => void;
  onFocusDone: () => void;
}) {
  const layout = useMemo(() => layoutTree(nodes), [nodes]);
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
    if (autoFit) fit();
  }, [autoFit, fit]);

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

      <div className={`map ${selectedId ? 'map--dimmed' : ''}`} ref={viewport}>
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
              />
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

function NodeBox({ box, seed, focused, selected, onOpen }: { box: Box; seed: boolean; focused: boolean; selected: boolean; onOpen: (id: string) => void }) {
  const { node, depth } = box;
  const cls = [
    'node',
    depth === 0 ? 'node--root' : depth === 1 ? 'node--l1' : 'node--l2',
    `node--${node.status}`,
    seed ? 'node--seed' : '',
    focused ? 'node--focus' : '',
    selected ? 'node--selected' : '',
  ].join(' ');

  return (
    <button
      data-node={node.id}
      className={cls}
      style={{ left: box.x, top: box.y, width: box.w, minHeight: box.h }}
      onClick={() => !seed && onOpen(node.id)}
      aria-label={node.status === 'corrected' ? `${node.label} (corrected)` : node.label}
    >
      {node.status === 'corrected' && node.correction ? (
        <>
          <span className="node__badge">
            <IconPencil size={14} />
            CORRECTED
          </span>
          <span className="node__label">{node.label}</span>
          <span className="node__said">
            You said: <s>{node.correction.said}</s>
          </span>
          <span className="node__actually">{node.correction.actually}</span>
        </>
      ) : (
        <>
          <span className="node__text">
            <span className="node__label">{node.label}</span>
            {node.subtitle && <span className="node__sub">{node.subtitle}</span>}
          </span>
          {node.status === 'new' && <span className="node__new">New</span>}
          {!!node.hiddenChildren && <span className="node__more">+{node.hiddenChildren}</span>}
        </>
      )}
    </button>
  );
}

function Legend() {
  return (
    <div className="legend">
      <span>
        <i className="legend__swatch legend__swatch--fix" /> Corrected
      </span>
      <span>
        <i className="legend__swatch legend__swatch--new" /> New from our chat
      </span>
      <span>
        <i className="legend__more">+2</i> Hidden — tap to open
      </span>
    </div>
  );
}
