import { useStore } from '../state/store';
import { IconChat, IconSidebar } from './Icons';
import './Header.css';

/** Top bar: "Past sessions" on the LEFT, logo on the RIGHT (the material box sits under the logo). */
export function Header() {
  const { state, dispatch, goHome } = useStore();
  return (
    <header className="header">
      <div className="header__left"><button className="btn header__sessions" onClick={() => dispatch({ type: 'ui.drawer', open: true })} aria-label="Open past sessions">
        <IconSidebar />
        <span className="header__sessions-label">Past sessions</span>
      </button>
      {state.screen === 'study' && <button className="btn" onClick={() => dispatch({ type: 'ui.history', open: !state.historyOpen })} aria-label="Conversation history" aria-expanded={state.historyOpen}>
        <IconChat /><span className="header__sessions-label">Conversation</span>
      </button>}</div>
      <button className="header__logo" onClick={goHome} aria-label="DysCover home">
        <span className="header__mark" aria-hidden="true" />
        <span className="header__name">DysCover</span>
      </button>
    </header>
  );
}
