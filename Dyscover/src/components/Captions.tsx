import { useLayoutEffect, useRef, useState, useEffect, type CSSProperties } from 'react';
import type { Caption, VoiceStatus } from '../types';
import './Captions.css';

/**
 * Live subtitles above the dock.
 *  - Assistant line: rolls during speech, then stays until the next reply so slower readers can finish it.
 *  - Learner line: small grey "YOU" line so they can check they were heard correctly.
 *    It fades out a few seconds after it is final. Can be turned off in the sidebar.
 */
export function Captions({
  user,
  assistant,
  status,
  pendingAction,
  showUser,
  beside,
}: {
  user: Caption | null;
  assistant: Caption | null;
  status: VoiceStatus;
  pendingAction: 'expand' | 'learn' | null;
  showUser: boolean;
  /** true when the node panel is open on the right: keep the text out from under it */
  beside?: boolean;
}) {
  const [userVisible, setUserVisible] = useState(false);
  useEffect(() => {
    if (!showUser || !user) { setUserVisible(false); return; }
    setUserVisible(true);
    if (user.final) {
      const timer = window.setTimeout(() => setUserVisible(false), 2000);
      return () => window.clearTimeout(timer);
    }
  }, [showUser, user?.text, user?.final]);

  return (
    <div className={`captions ${beside ? 'captions--beside' : ''}`} aria-live="polite">
      {pendingAction ? <p className="captions__assistant">{pendingAction === 'expand' ? 'Expanding subtopics…' : 'Preparing explanation…'}</p>
        : status === 'thinking' ? <p className="captions__assistant">Thinking…</p>
        : userVisible && user && status !== 'speaking' ? <RollingLine text={user.text} maxLines={1} className="captions__user" prefix="YOU" />
          : assistant && <RollingLine text={assistant.text} maxLines={1} className="captions__assistant" />}
    </div>
  );
}

function RollingLine({ text, maxLines, className, prefix }: { text: string; maxLines: number; className: string; prefix?: string }) {
  const ref = useRef<HTMLParagraphElement>(null);
  const [visible, setVisible] = useState(text);

  useLayoutEffect(() => {
    const target = ref.current;
    if (!target) return;
    const update = () => {
      const probe = target.cloneNode(false) as HTMLParagraphElement;
      probe.style.position = 'fixed';
      probe.style.left = '-10000px';
      probe.style.width = `${target.getBoundingClientRect().width}px`;
      probe.style.maxHeight = 'none';
      probe.style.visibility = 'hidden';
      if (prefix) {
        const label = document.createElement('span');
        label.className = 'captions__you';
        label.textContent = prefix;
        probe.append(label);
      }
      const content = document.createTextNode('');
      probe.append(content);
      document.body.append(probe);
      const limit = parseFloat(getComputedStyle(target).lineHeight) * maxLines + 1;
      const fits = (value: string) => {
        content.textContent = value;
        return probe.getBoundingClientRect().height <= limit;
      };
      let result = text;
      if (!fits(result)) {
        const words = text.trim().split(/\s+/);
        let low = 0, high = words.length - 1;
        while (low < high) {
          const mid = Math.floor((low + high) / 2);
          if (fits(`… ${words.slice(mid).join(' ')}`)) high = mid;
          else low = mid + 1;
        }
        result = `… ${words.slice(low).join(' ')}`;
        if (!fits(result)) {
          const last = words[words.length - 1] ?? '';
          let start = 0, end = last.length;
          while (start < end) {
            const mid = Math.floor((start + end) / 2);
            if (fits(`… ${last.slice(mid)}`)) end = mid;
            else start = mid + 1;
          }
          result = `… ${last.slice(start)}`;
        }
      }
      probe.remove();
      setVisible(result);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(target);
    return () => observer.disconnect();
  }, [text, maxLines, prefix]);

  return <p ref={ref} className={className} style={{ '--caption-lines': maxLines } as CSSProperties}>{prefix && <span className="captions__you">{prefix}</span>}{visible}</p>;
}
