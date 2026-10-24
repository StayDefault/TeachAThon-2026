import { useEffect, useState } from 'react';
import { api } from '../api';
import type { ChatMessage } from '../types';
import { replay, stopReplay } from '../lib/speech';
import { IconClose, IconPlay } from './Icons';
import './NodePanel.css';

export function ConversationHistory({ sessionId, liveMessages = [], onClose }: { sessionId: string; liveMessages?: ChatMessage[]; onClose: () => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    api.getHistory(sessionId).then(value => { if (alive) { setMessages([...value]); setError(''); } })
      .catch((cause: unknown) => { if (alive) setError(cause instanceof Error ? cause.message : 'Could not load conversation.'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [sessionId]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => { window.removeEventListener('keydown', onKey); };
  }, [onClose]);
  useEffect(() => () => stopReplay(), []);
  const transcript = [...new Map([...messages, ...liveMessages].map(item => [item.id, item])).values()].sort((a, b) => a.at.localeCompare(b.at));
  return <aside className="panel" aria-label="Conversation history">
    <div className="panel__head">
      <h2 className="panel__title">Conversation</h2>
      <button className="panel__close" onClick={onClose} aria-label="Close conversation history"><IconClose /></button>
    </div>
    <div className="panel__body">
      {error && <p role="alert">{error}</p>}
      {!transcript.length ? <p role={loading ? 'status' : undefined}>{loading ? 'Loading conversation…' : 'Your conversation will appear here.'}</p>
        : <div className="panel__chat">{transcript.map(item => <div key={item.id} className={`bubble bubble--${item.role === 'user' ? 'user' : 'ai'}`}>
          {item.role === 'assistant' && <button className="bubble__play" aria-label="Play this reply" onClick={() => replay(item.text, item.audioUrl)}><IconPlay /></button>}
          <span><strong>{item.role === 'user' ? 'You' : 'Dyscover'}</strong><br />{item.text}</span>
        </div>)}</div>}
    </div>
  </aside>;
}
