import { useState, type FormEvent } from 'react';
import type { VoiceStatus } from '../types';
import { useLevel } from '../state/level';
import { Orb } from './Orb';
import { IconArrowRight, IconKeyboard } from './Icons';
import './VoiceDock.css';

const STATUS_LABEL: Record<VoiceStatus, string> = {
  idle: 'Ready',
  connecting: 'Connecting…',
  listening: 'Listening',
  thinking: 'Thinking…',
  speaking: 'Speaking',
  ended: 'Session ended',
};

// Per-bar height multipliers so the waveform looks organic.
const LEFT = [0.35, 0.7, 1, 0.75, 0.45];
const RIGHT = [0.45, 0.75, 1, 0.7, 0.35];

/**
 * The glass dock at the bottom. Voice mode is hands-free; text mode stops the mic.
 * - Voice mode (default): keyboard 1 : voice 9. Tapping the voice area ends / resumes the session.
 * - Text mode (optional): input 9 : mini orb 1. Tapping the mini orb returns to voice.
 */
export function VoiceDock(props: {
  status: VoiceStatus;
  mode: 'voice' | 'text';
  onModeChange: (mode: 'voice' | 'text') => void;
  onToggleSession: () => void;
  onSendText: (text: string) => void;
  placeholder?: string;
}) {
  const { status, mode, onModeChange, onToggleSession, onSendText } = props;
  const [draft, setDraft] = useState('');
  const [submitted, setSubmitted] = useState('');
  const ended = status === 'ended';
  const isVoice = mode === 'voice';

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    setSubmitted(text);
    onSendText(text);
    setDraft('');
  };

  return (
    <div className={`dock ${!isVoice && submitted ? 'dock--submitted' : ''}`} role="group" aria-label="Talk to DysCover">
      {!isVoice && submitted && <details className="dock__submitted" aria-label="Your latest submitted message" aria-live="polite">
        <summary><span>You</span> {submitted}</summary>
        <p>{submitted}</p>
      </details>}
      <div className="dock__seg" style={{ flexGrow: isVoice ? 1 : 9 }}>
        {isVoice ? (
          <button className="dock__kbd" onClick={() => onModeChange('text')} aria-label="Switch to typing">
            <IconKeyboard size={22} />
          </button>
        ) : (
          <form className="dock__input" onSubmit={submit}>
            <label htmlFor="dock-input" className="sr-only">
              Type to DysCover
            </label>
            <input
              id="dock-input"
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={props.placeholder ?? "Type a question, or say what's confusing…"}
              autoComplete="off"
            />
            <button type="submit" className="dock__send" aria-label="Send">
              <IconArrowRight size={20} />
            </button>
          </form>
        )}
      </div>

      <span className="dock__divider" aria-hidden="true" />

      <div className="dock__seg" style={{ flexGrow: isVoice ? 9 : 1 }}>
        {isVoice ? (
          <button className="dock__voice" onClick={onToggleSession} aria-label={ended ? 'Resume voice session' : 'End voice session'}>
            <span className="dock__status">
              <span className={`dock__dot ${ended ? 'dock__dot--off' : ''}`} aria-hidden="true" />
              <span aria-live="polite">{STATUS_LABEL[status]}</span>
            </span>
            <Bars weights={LEFT} tone="cool" off={ended} />
            <Orb size={52} still={ended} />
            <Bars weights={RIGHT} tone="warm" off={ended} />
            <span className="dock__hint">{ended ? 'Tap to resume' : 'Tap to end'}</span>
          </button>
        ) : (
          <button className="dock__mini" onClick={() => onModeChange('voice')} aria-label="Back to voice">
            <Orb size={36} still={ended} reactive={false} />
          </button>
        )}
      </div>
    </div>
  );
}

function Bars({ weights, tone, off }: { weights: number[]; tone: 'cool' | 'warm'; off: boolean }) {
  const level = useLevel();
  return (
    <span className={`dock__bars dock__bars--${tone}`} aria-hidden="true" style={{ opacity: off ? 0.25 : 1 }}>
      {weights.map((w, i) => (
        <span key={i} style={{ height: `${Math.max(6, 32 * w * (0.25 + (off ? 0 : level) * 0.95))}px` }} />
      ))}
    </span>
  );
}
