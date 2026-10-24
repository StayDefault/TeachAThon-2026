import { useEffect, useState } from 'react';
import { api } from '../api';
import { useStore } from '../state/store';
import type { SessionSummary } from '../types';
import { IconPlus, IconSidebar } from './Icons';
import './SessionsSidebar.css';

function bucket(iso: string): 'Today' | 'This week' | 'Earlier' {
  const days = (Date.now() - new Date(iso).getTime()) / 86_400_000;
  if (days < 1 && new Date(iso).toDateString() === new Date().toDateString()) return 'Today';
  if (days < 7) return 'This week';
  return 'Earlier';
}

/** Left drawer (~1/6 of the screen). Closed by default; opens from the "Past sessions" button. */
export function SessionsSidebar() {
  const { state, dispatch, openPastSession, goHome } = useStore();
  const [sessions, setSessions] = useState<SessionSummary[] | null>(null);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    if (state.drawerOpen) {
      setError('');
      api.listSessions().then(setSessions).catch((cause: unknown) => {
        setSessions([]);
        setError(cause instanceof Error ? cause.message : 'Could not load past sessions.');
      });
    }
  }, [state.drawerOpen]);

  if (!state.drawerOpen) return null;
  const close = () => dispatch({ type: 'ui.drawer', open: false });
  const remove = async (s: SessionSummary) => {
    if (!window.confirm(`Delete “${s.title}” and its uploaded files? This cannot be undone.`)) return;
    setDeleting(s.id);
    setError('');
    try {
      await api.deleteSession(s.id);
      setSessions((current) => current?.filter((item) => item.id !== s.id) ?? null);
      if (state.session?.id === s.id) goHome();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not delete this session.');
    } finally {
      setDeleting(null);
    }
  };

  const groups: Record<string, SessionSummary[]> = {};
  for (const s of sessions ?? []) (groups[bucket(s.updatedAt)] ??= []).push(s);

  return (
    <>
      <button className="drawer-scrim" onClick={close} aria-label="Close past sessions" />
      <nav className="drawer" aria-label="Past sessions">
        <div className="drawer__head">
          <span className="drawer__title">Past sessions</span>
          <button className="drawer__close" onClick={close} aria-label="Close past sessions">
            <IconSidebar />
          </button>
        </div>
        <div className="drawer__new">
          <button className="btn drawer__newbtn" onClick={goHome}>
            <IconPlus size={18} />
            New session
          </button>
        </div>
        <div className="drawer__list">
          {sessions === null && <p className="drawer__empty">Loading…</p>}
          {error && <p className="drawer__empty" role="alert">{error}</p>}
          {!error && sessions?.length === 0 && <p className="drawer__empty">No sessions yet.</p>}
          {(['Today', 'This week', 'Earlier'] as const).map(
            (g) =>
              groups[g] && (
                <section key={g}>
                  <h3 className="drawer__group">{g.toUpperCase()}</h3>
                  {groups[g].map((s) => (
                    <div className="drawer__row" key={s.id}>
                      <button
                        className={`drawer__item ${state.session?.id === s.id ? 'drawer__item--active' : ''}`}
                        onClick={() => openPastSession(s.id).catch((cause: unknown) =>
                          setError(cause instanceof Error ? cause.message : 'Could not open this session.'))}
                      >
                        <span className="drawer__item-title">{s.title}</span>
                        <span className="drawer__item-meta">
                          {s.topic}
                          {s.durationMin ? ` · ${s.durationMin} min` : ''}
                        </span>
                      </button>
                      <button className="drawer__delete" aria-label={`Delete ${s.title}`} disabled={deleting === s.id} onClick={() => void remove(s)}>Delete</button>
                    </div>
                  ))}
                </section>
              ),
          )}
        </div>
        <label className="drawer__toggle">
          <input
            type="checkbox"
            checked={state.showUserCaptions}
            onChange={(e) => dispatch({ type: 'ui.userCaptions', show: e.target.checked })}
          />
          Show my captions
        </label>
      </nav>
    </>
  );
}
