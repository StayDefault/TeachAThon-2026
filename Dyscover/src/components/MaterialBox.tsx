import { useLayoutEffect, useRef, useState } from 'react';
import type { Material } from '../types';
import { IconBox } from './Icons';
import './MaterialBox.css';

/**
 * The small "study box" under the logo (top-right) holding the uploaded files.
 * With `flyIn`, it starts big in the middle of the screen (where it sat on Home)
 * and flies into the corner.
 */
export function MaterialBox({ title, materials, flyIn }: { title: string; materials: Material[]; flyIn: boolean }) {
  const ref = useRef<HTMLButtonElement>(null);
  const [vars, setVars] = useState<Record<string, string> | null>(null);

  useLayoutEffect(() => {
    if (!flyIn || !ref.current) return;
    const box = ref.current.querySelector('.mbox__square') as HTMLElement;
    const r = box.getBoundingClientRect();
    const fromX = window.innerWidth / 2 - (r.left + r.width / 2);
    const fromY = window.innerHeight * 0.42 - (r.top + r.height / 2);
    setVars({ '--fx': `${fromX}px`, '--fy': `${fromY}px` });
  }, [flyIn]);

  const [open, setOpen] = useState(false);

  return (
    <div className="mbox">
      <button
        ref={ref}
        className={`mbox__btn ${flyIn ? 'mbox__btn--fly' : ''} ${flyIn && !vars ? 'mbox__btn--pre' : ''}`}
        style={vars ?? undefined}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={`Materials: ${materials.length} files`}
      >
        <span className="mbox__label">
          <span className="mbox__title">{title}</span>
          <span className="mbox__meta">{materials.length} files · read</span>
        </span>
        <span className="mbox__square">
          <IconBox size={26} />
          <span className="mbox__count">{materials.length}</span>
        </span>
      </button>
      {open && (
        <ul className="mbox__list">
          {materials.map((m) => (
            <li key={m.id}>
              <span className="mbox__file">{m.name}</span>
              <span className="mbox__kind">{m.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
