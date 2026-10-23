import { useEffect, useState, type FormEvent } from 'react';
import { useStore } from './state/store';
import { Header } from './components/Header';
import { SessionsSidebar } from './components/SessionsSidebar';
import { Captions } from './components/Captions';
import { VoiceDock } from './components/VoiceDock';
import { HomeScreen } from './screens/HomeScreen';
import { StudyScreen } from './screens/StudyScreen';
import { isMock } from './api';

const requiresLogin = !isMock || import.meta.env.VITE_REQUIRE_LOGIN === 'true';

export function App() {
  const [signedIn, setSignedIn] = useState(!requiresLogin);
  const [checkingLogin, setCheckingLogin] = useState(requiresLogin);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const { state, dispatch, send } = useStore();
  const inSession = state.screen === 'study';

  const toggleSession = () => {
    const ending = state.voice !== 'ended';
    dispatch({ type: 'local.voice', status: ending ? 'ended' : 'listening' });
    if (inSession) send({ type: ending ? 'session.end' : 'session.resume' });
  };

  const sendText = (text: string) => {
    if (inSession) {
      send({ type: 'user.text', text });
    } else {
      dispatch({ type: 'local.caption', caption: { role: 'user', text, final: true } });
      dispatch({ type: 'local.caption', caption: { role: 'assistant', text: 'Drop your files on the board first, then we can start.', final: true } });
    }
  };

  useEffect(() => {
    if (!requiresLogin) return;
    fetch('/api/auth/status').then((response) => setSignedIn(response.ok))
      .catch(() => setLoginError('Cannot reach the Dyscover server.'))
      .finally(() => setCheckingLogin(false));
  }, []);

  const signIn = async (event: FormEvent) => {
    event.preventDefault();
    setLoginError('');
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        const error: unknown = await response.json().catch(() => null);
        const detail = error && typeof error === 'object' && 'detail' in error && typeof error.detail === 'string'
          ? error.detail : `Sign-in failed (${response.status}).`;
        throw new Error(detail);
      }
      setPassword('');
      setSignedIn(true);
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'Sign-in failed.');
    }
  };

  if (checkingLogin) return <main className="board"><p className="judge-login">Checking access…</p></main>;
  if (!signedIn) return (
    <main className="board">
      <form className="judge-login" onSubmit={signIn}>
        <h1>Dyscover</h1>
        <p>Sign in to explore the prototype.</p>
        <label htmlFor="judge-email">Email</label>
        <input id="judge-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="username" />
        <label htmlFor="judge-password">Password</label>
        <input id="judge-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" />
        <button type="submit">Sign in</button>
        {loginError && <p role="alert">{loginError}</p>}
      </form>
    </main>
  );

  return (
    <main className="board">
      <Header />
      {inSession ? <StudyScreen key={state.session?.id} /> : <HomeScreen />}

      <Captions user={state.captions.user} assistant={state.captions.assistant} showUser={state.showUserCaptions} beside={!!state.openNodeId} />
      <VoiceDock
        status={state.voice}
        mode={state.inputMode}
        onModeChange={(mode) => dispatch({ type: 'ui.inputMode', mode })}
        onToggleSession={toggleSession}
        onSendText={sendText}
        placeholder={inSession ? 'Ask about the map, or say what’s confusing…' : undefined}
      />

      <SessionsSidebar />
      {state.error && <p className="backend-error" role="alert">{state.error}</p>}
      <span className="demo-chip">{isMock ? 'Demo mode · scripted backend' : 'AI-generated voice · Files sent to OpenAI'}</span>
    </main>
  );
}
