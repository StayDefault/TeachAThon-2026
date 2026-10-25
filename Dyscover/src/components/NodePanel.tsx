import { useEffect, useState } from 'react';
import { api } from '../api';
import { replay, stopReplay } from '../lib/speech';
import type { MapNode, NodeDetail } from '../types';
import { IconClose, IconFile, IconPlay } from './Icons';
import './NodePanel.css';

/**
 * Quarter-screen panel shown when a node is clicked:
 *   1. where it comes from in the learner's files (highlighted quote)
 *   2. a short summary
 */
export function NodePanel({ sessionId, nodeId, node, childNodes = [], onClose, onEdit, onAdd, onRemove, onKeep, onExpand, onLearn, onSelect }: {
  sessionId: string; nodeId: string; onClose: () => void;
  node?: MapNode;
  onEdit: (label: string, summary: string) => void;
  onAdd: (label: string) => void;
  onRemove?: () => void;
  onKeep: () => void;
  childNodes?: MapNode[];
  onExpand: () => void;
  onLearn: () => void;
  onSelect: (nodeId: string) => void;
}) {
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState('');
  const [summary, setSummary] = useState('');
  const [childLabel, setChildLabel] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    setDetail(null);
    setError('');
    setConfirmDelete(false);
    let alive = true;
    api.getNodeDetail(sessionId, nodeId).then((d) => { if (alive) { setDetail(d); setLabel(d.title); setSummary(d.summary); setEditing(false); setChildLabel(''); } })
      .catch((cause: unknown) => alive && setError(cause instanceof Error ? cause.message : 'Could not load node details.'));
    return () => {
      alive = false;
      stopReplay();
    };
  }, [sessionId, nodeId]);

  useEffect(() => {
    if (!detail || node?.userEdited !== false) return;
    let alive = true;
    api.getNodeDetail(sessionId, nodeId).then((value) => { if (alive) { setDetail(value); setLabel(value.title); setSummary(value.summary); } })
      .catch((cause: unknown) => alive && setError(cause instanceof Error ? cause.message : 'Could not refresh node details.'));
    return () => { alive = false; };
  }, [sessionId, nodeId, node?.userEdited, node?.correction?.actually]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const sourceUrl = detail?.source ? api.materialUrl(sessionId, detail.source.materialId) : '';
  const correction = node ? node.correction : detail?.correction;

  return (
    <aside className="panel" aria-label={detail ? `${detail.title} details` : 'Node details'}>
      <div className="panel__head">
        <div>
          {detail && detail.breadcrumb.length > 0 && <div className="panel__crumb">{detail.breadcrumb.join(' › ')} ›</div>}
          <h2 className="panel__title">{detail?.title ?? '…'}</h2>
        </div>
        <div className="panel__actions">
          <button className="btn" onClick={() => detail && replay(detail.summary)} disabled={!detail}>
            <IconPlay />
            Hear it again
          </button>
          <button className="panel__close" onClick={onClose} aria-label="Close">
            <IconClose size={18} />
          </button>
        </div>
      </div>

      {error ? (
        <div className="panel__body" role="alert">{error}</div>
      ) : !detail ? (
        <div className="panel__body">
          <div className="panel__skeleton" />
          <div className="panel__skeleton panel__skeleton--short" />
        </div>
      ) : (
        <div className="panel__body">
          <section className="panel__concept">
            <h3 className="panel__h">{(node?.userEdited ?? detail.userEdited) ? 'YOUR MAP NOTE' : 'WHAT IT MEANS'}</h3>
            <p className="panel__summary">{detail.summary}</p>
            {correction && <p className="panel__correction"><strong>Correction:</strong> {correction.actually}</p>}
          </section>

          <section className="panel__explore">
            <h3 className="panel__h">CHOOSE WHAT TO DO NEXT</h3>
            <button className="btn" onClick={onExpand}>Expand subtopics</button>
            <button className="btn" onClick={onLearn}>Learn this topic</button>
            {childNodes.length > 0 && <>
              <p>Choose a subtopic to inspect, expand, or learn.</p>
              <ul className="panel__branches">{childNodes.map(child => <li key={child.id}>
                <button className="btn" aria-label={`Open subtopic ${child.label}`} onClick={() => onSelect(child.id)}>{child.label}</button>
              </li>)}</ul>
            </>}
          </section>

          <section className="panel__edit">
            <button className="btn" onClick={() => setEditing((value) => !value)}>{editing ? 'Cancel editing' : 'Edit this node'}</button>
            {editing && <form onSubmit={(event) => {
              event.preventDefault();
              if (!label.trim() || !summary.trim()) return;
              onEdit(label.trim(), summary.trim());
              setDetail({ ...detail, title: label.trim(), summary: summary.trim(), userEdited: true, correction: undefined });
              setEditing(false);
            }}>
              <label htmlFor="node-label">Short label</label>
              <input id="node-label" value={label} onChange={(event) => setLabel(event.target.value)} maxLength={60} required />
              <label htmlFor="node-summary">Brief description</label>
              <textarea id="node-summary" value={summary} onChange={(event) => setSummary(event.target.value)} maxLength={600} rows={4} required />
              <button className="btn" type="submit" disabled={label.trim().split(/\s+/).length > 5}>Save changes</button>
            </form>}
            <form onSubmit={(event) => { event.preventDefault(); if (childLabel.trim()) { onAdd(childLabel.trim()); setChildLabel(''); } }}>
              <label htmlFor="node-child">Add a connected idea</label>
              <input id="node-child" value={childLabel} onChange={(event) => setChildLabel(event.target.value)} maxLength={60} placeholder="New idea" required />
              <button className="btn" type="submit" disabled={childLabel.trim().split(/\s+/).length > 5}>Add node</button>
            </form>
            {onRemove && (node?.pendingRemoval || confirmDelete ? <div className="panel__deletion" role="group" aria-label="Confirm node deletion">
              <p>{node?.pendingRemoval || 'Delete this node?'} This also deletes its connected branches.</p>
              <button className="btn panel__remove" onClick={onRemove}>Confirm deletion</button>
              <button className="btn" onClick={() => { setConfirmDelete(false); if (node?.pendingRemoval) onKeep(); }}>Keep node</button>
            </div> : <button className="btn panel__remove" onClick={() => setConfirmDelete(true)}>Delete this node and its branches</button>)}
          </section>

          {detail.source && (
            <section>
              <h3 className="panel__h">FROM YOUR MATERIAL</h3>
              {(node?.userEdited ?? detail.userEdited) && <p className="panel__source-note">This is the original citation. Your edited description has not been checked against it.</p>}
              <div className="panel__slide">
                {detail.source.context && <span className="panel__slide-ctx">{detail.source.context}</span>}
                {sourceUrl && detail.source.fileName.match(/\.(png|jpe?g|webp)$/i)
                  ? <img className="panel__source-image" src={sourceUrl} alt={`Original source: ${detail.source.fileName}`} />
                  : <p className="panel__quote"><mark>{detail.source.quote}</mark></p>}
              </div>
              <div className="panel__ref">
                <IconFile size={18} />
                {sourceUrl ? <a href={sourceUrl} target="_blank" rel="noopener noreferrer">
                  {detail.source.fileName}
                  {detail.source.page ? ` · ${detail.source.fileName.toLowerCase().endsWith('.pptx') ? 'slide' : 'page'} ${detail.source.page}` : ''}
                  {' ↗'}
                </a> : <span>{detail.source.fileName}</span>}
              </div>
            </section>
          )}
          {!detail.source && detail.userEdited && <p className="panel__source-note">No verified source citation for this idea yet.</p>}

        </div>
      )}
    </aside>
  );
}
