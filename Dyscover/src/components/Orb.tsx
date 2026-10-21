import { useLevel } from '../state/level';
import './Orb.css';

/**
 * The iridescent voice orb. It slowly spins and scales with live loudness (level 0..1).
 * `still` freezes it (session ended). Also used small as the logo.
 */
export function Orb({ size = 52, still = false, reactive = true }: { size?: number; still?: boolean; reactive?: boolean }) {
  const level = useLevel();
  const scale = still || !reactive ? 1 : 1 + level * 0.28;
  return (
    <span
      className={`orb ${still ? 'orb--still' : ''}`}
      style={{ width: size, height: size, transform: `scale(${scale})` }}
      aria-hidden="true"
    >
      <span className="orb__glow" />
      <span className="orb__core" />
      <span className="orb__shine" />
    </span>
  );
}
