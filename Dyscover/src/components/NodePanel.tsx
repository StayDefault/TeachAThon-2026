import { useEffect, useState } from 'react';
import { api } from '../api';
import { replay, stopReplay } from '../lib/speech';
import type { NodeDetail } from '../types';
import { IconClose, IconFile, IconPlay } from './Icons';
import './NodePanel.css';

/**
 * Quarter-screen panel shown when a node is clicked:
 *   1. where it comes from in the learner's files (highlighted quote)
 *   2. a short summary
 *   3. the conversation about this node (each reply can be replayed)
 */
export function NodePanel({ sessionId, nodeId, onClose }: { sessionId: string; nodeId: string; onClose: () => void }) {
  const [detail, setDetail] = useState<NodeDetail | null>(null);

  useEffect(() => {
    setDetail(null);
    let alive = true;
    api.getNodeDetail(sessionId, nodeId).then((d) => alive && setDetail(d));
    return () => {
      alive = false;
      stopReplay();
    };
  }, [sessionId, nodeId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

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

      {!detail ? (
        <div className="panel__body">
          <div className="panel__skeleton" />
          <div className="panel__skeleton panel__skeleton--short" />
        </div>
      ) : (
        <div className="panel__body">
          {detail.source && (
            <section>
              <h3 className="panel__h">FROM YOUR SLIDES</h3>
              <div className="panel__slide">
                {detail.source.context && <span className="panel__slide-ctx">{detail.source.context}</span>}
                <span className="panel__bar" style={{ width: '70%' }} aria-hidden="true" />
                <span className="panel__bar" style={{ width: '52%' }} aria-hidden="true" />
                <p className="panel__quote">
                  <mark>{detail.source.quote}</mark>
                </p>
                <span className="panel__bar" style={{ width: '60%' }} aria-hidden="true" />
              </div>
              <div className="panel__ref">
                <IconFile size={18} />
                <span>
                  {detail.source.fileName}
                  {detail.source.page ? ` · slide ${detail.source.page}` : ''}
                </span>
              </div>
            </section>
          )}

          <section>
            <h3 className="panel__h">IN SHORT</h3>
            <p className="panel__summary">{detail.summary}</p>
          </section>

          {detail.messages.length > 0 && (
            <section>
              <h3 className="panel__h">OUR CONVERSATION</h3>
              <div className="panel__chat">
                {detail.messages.map((m) =>
                  m.role === 'user' ? (
                    <div key={m.id} className="bubble bubble--user">
                      {m.text}
                    </div>
                  ) : (
                    <div key={m.id} className="bubble bubble--ai">
                      <button className="bubble__play" onClick={() => replay(m.text, m.audioUrl)} aria-label="Play this reply">
                        <IconPlay />
                      </button>
                      <span>{m.text}</span>
                    </div>
                  ),
                )}
              </div>
            </section>
          )}
        </div>
      )}
    </aside>
  );
}
