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
export function NodePanel({ sessionId, nodeId, node, childNodes = [], pendingAction, onClose, onKeep, onRemove, onExpand, onLearn, onSelect }: {
  sessionId: string; nodeId: string; onClose: () => void;
  node?: MapNode;
  pendingAction: 'expand' | 'learn' | null;
  onRemove: () => void;
  onKeep: () => void;
  childNodes?: MapNode[];
  onExpand: () => void;
  onLearn: () => void;
  onSelect: (nodeId: string) => void;
}) {
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    setDetail(null);
    setError('');
    let alive = true;
    api.getNodeDetail(sessionId, nodeId).then((d) => { if (alive) setDetail(d); })
      .catch((cause: unknown) => alive && setError(cause instanceof Error ? cause.message : 'Could not load node details.'));
    return () => {
      alive = false;
      stopReplay();
    };
  }, [sessionId, nodeId]);

  useEffect(() => {
    if (!detail || node?.userEdited !== false) return;
    let alive = true;
    api.getNodeDetail(sessionId, nodeId).then((value) => { if (alive) setDetail(value); })
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
            <button className="btn" onClick={onExpand} disabled={!!pendingAction}>Expand subtopics</button>
            <button className="btn" onClick={onLearn} disabled={!!pendingAction}>Learn this topic</button>
            {pendingAction && <p className="panel__pending" role="status">{pendingAction === 'expand' ? 'Expanding subtopics…' : 'Preparing explanation…'}</p>}
            {childNodes.length > 0 && <>
              <p>Choose a subtopic to inspect, expand, or learn.</p>
              <ul className="panel__branches">{childNodes.map(child => <li key={child.id}>
                <button className="btn" aria-label={`Open subtopic ${child.label}`} onClick={() => onSelect(child.id)}>{child.label}</button>
              </li>)}</ul>
            </>}
          </section>

          {node?.pendingRemoval && <section className="panel__deletion" role="group" aria-label="Confirm node deletion">
              <p>{node.pendingRemoval} This also deletes its connected branches.</p>
              <button className="btn panel__remove" onClick={onRemove}>Confirm deletion</button>
              <button className="btn" onClick={onKeep}>Keep node</button>
          </section>}

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
