import { useStore } from './state/store';
import { Header } from './components/Header';
import { SessionsSidebar } from './components/SessionsSidebar';
import { Captions } from './components/Captions';
import { VoiceDock } from './components/VoiceDock';
import { HomeScreen } from './screens/HomeScreen';
import { StudyScreen } from './screens/StudyScreen';
import { isMock } from './api';

export function App() {
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
      {isMock && <span className="demo-chip">Demo mode · scripted backend</span>}
    </main>
  );
}
