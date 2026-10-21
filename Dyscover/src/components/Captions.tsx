import type { Caption } from '../types';
import './Captions.css';

/**
 * Live subtitles above the dock.
 *  - Assistant line: large, always shown — every spoken word is also readable.
 *  - Learner line: small grey "YOU" line so they can check they were heard correctly.
 *    It fades out a few seconds after it is final. Can be turned off in the sidebar.
 */
export function Captions({
  user,
  assistant,
  showUser,
  beside,
}: {
  user: Caption | null;
  assistant: Caption | null;
  showUser: boolean;
  /** true when the node panel is open on the right: keep the text out from under it */
  beside?: boolean;
}) {
  return (
    <div className={`captions ${beside ? 'captions--beside' : ''}`} aria-live="polite">
      {showUser && user && (
        <p key={user.final ? `f-${user.text}` : 'live'} className={`captions__user ${user.final ? 'captions__user--final' : ''}`}>
          <span className="captions__you">YOU</span>
          {user.text}
        </p>
      )}
      {assistant && <p className="captions__assistant">{assistant.text}</p>}
    </div>
  );
}
