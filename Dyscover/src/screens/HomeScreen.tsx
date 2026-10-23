import { useEffect, useRef, useState, type DragEvent } from 'react';
import { useStore } from '../state/store';
import { useLocalSpeech } from '../lib/useLocalSpeech';
import { IconArrowRight, IconBox, IconFile, IconImage } from '../components/Icons';
import { DEMO_MATERIALS } from '../api/mockData';
import { isMock } from '../api';
import './HomeScreen.css';

interface Card {
  id: number;
  file: File;
  x: number; // board coords of the card's centre where it landed
  y: number;
  flying: boolean;
}

let nextId = 1;

function labelFor(file: File) {
  if (file.type.startsWith('image/')) return 'Image';
  if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) return 'PDF';
  return 'Document';
}

/**
 * Home: whiteboard + greeting. Files dropped anywhere on the board land as cards,
 * then fly and shrink into the study box. Then the learner starts studying.
 */
export function HomeScreen() {
  const { startNewSession } = useStore();
  const { speak } = useLocalSpeech();
  const boardRef = useRef<HTMLDivElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [cards, setCards] = useState<Card[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [gulp, setGulp] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState('');

  useEffect(() => {
    speak("Hello! Drag your slides, handouts or photos onto the board — I'll pack them into the box and read them.");
  }, [speak]);

  const boxCentre = () => {
    const b = boxRef.current!.getBoundingClientRect();
    const o = boardRef.current!.getBoundingClientRect();
    return { x: b.left - o.left + b.width / 2, y: b.top - o.top + b.height / 2 };
  };

  const addFiles = (incoming: File[], at?: { x: number; y: number }) => {
    if (!incoming.length) return;
    const c = boxCentre();
    const spawn = incoming.map((file, i) => {
      // Scatter around the drop point, or along an arc above the box if no point was given.
      const n = incoming.length;
      const angle = n === 1 ? Math.PI * 1.5 : Math.PI * 1.05 + (i / (n - 1)) * Math.PI * 0.9;
      const base = at ?? { x: c.x + Math.cos(angle) * 400, y: c.y + Math.sin(angle) * 150 };
      const jitter = at ? { x: (i % 2 ? 1 : -1) * 40 * i, y: i * 26 } : { x: 0, y: 0 };
      return { id: nextId++, file, x: base.x + jitter.x, y: base.y + jitter.y, flying: false };
    });
    setCards((cs) => [...cs, ...spawn]);
    // Let them land, then fly in one after another.
    spawn.forEach((card, i) => {
      setTimeout(() => setCards((cs) => cs.map((x) => (x.id === card.id ? { ...x, flying: true } : x))), 700 + i * 180);
    });
    const total = files.length + incoming.length;
    setFiles((f) => [...f, ...incoming]);
    setTimeout(
      () => speak(`Got ${total} ${total === 1 ? 'file' : 'files'}. Tap Start when you're ready — or just say "let's start".`),
      900 + spawn.length * 180,
    );
  };

  const onLanded = (id: number) => {
    setCards((cs) => cs.filter((c) => c.id !== id));
    setGulp((g) => g + 1);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const o = boardRef.current!.getBoundingClientRect();
    addFiles(Array.from(e.dataTransfer.files), { x: e.clientX - o.left, y: e.clientY - o.top });
  };

  const useDemoFiles = () => {
    const demo = DEMO_MATERIALS.map(
      (m) => new File([''], m.name, { type: m.kind === 'image' ? 'image/jpeg' : 'application/pdf' }),
    );
    addFiles(demo);
  };

  const start = async () => {
    setStarting(true);
    setStartError('');
    try {
      await startNewSession(files);
    } catch (error) {
      setStartError(error instanceof Error ? error.message : 'Could not start this session');
      setStarting(false);
    }
  };

  const inBox = files.length - cards.length;
  const c = boxRef.current && boardRef.current ? boxCentre() : null;

  return (
    <div
      ref={boardRef}
      className={`home ${dragOver ? 'home--over' : ''}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={(e) => {
        if (e.currentTarget === e.target) setDragOver(false);
      }}
      onDrop={onDrop}
    >
      <div className="home__greet">
        <h1>Hello, what can I help you with today?</h1>
        <p>Drop your materials anywhere on the board.</p>
      </div>

      <div ref={boxRef} className="home__box" key={gulp} data-gulp={gulp > 0}>
        <IconBox size={36} />
        <span className={inBox > 0 ? 'home__count' : 'home__drop'}>
          {inBox > 0 ? `${inBox} ${inBox === 1 ? 'file' : 'files'}` : dragOver ? 'Drop to add' : 'Drop here'}
        </span>
      </div>
      <p className="home__boxlabel">Your study box</p>

      {cards.map((card) => (
        <div
          key={card.id}
          className={`fcard ${card.flying ? 'fcard--fly' : ''}`}
          style={
            {
              left: card.x,
              top: card.y,
              '--dx': c ? `${c.x - card.x}px` : '0px',
              '--dy': c ? `${c.y - card.y}px` : '0px',
            } as React.CSSProperties
          }
          onTransitionEnd={(e) => e.propertyName === 'transform' && card.flying && onLanded(card.id)}
        >
          {card.file.type.startsWith('image/') ? <IconImage size={22} className="fcard__icon fcard__icon--img" /> : <IconFile size={22} className="fcard__icon" />}
          <span className="fcard__text">
            <span className="fcard__name">{card.file.name}</span>
            <span className="fcard__kind">{labelFor(card.file)}</span>
          </span>
        </div>
      ))}

      <div className="home__actions">
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.pptx,.txt,.md,.png,.jpg,.jpeg,.webp"
          hidden
          onChange={(e) => {
            addFiles(Array.from(e.target.files ?? []));
            e.target.value = '';
          }}
        />
        <button className="btn btn--lg" onClick={() => inputRef.current?.click()}>
          Browse files
        </button>
        {files.length === 0 && isMock ? (
          <button className="btn btn--lg" onClick={useDemoFiles}>
            Use demo files
          </button>
        ) : files.length > 0 ? (
          <button className="btn btn--lg btn--primary" onClick={start} disabled={starting || inBox < files.length}>
            {starting ? 'Reading…' : 'Start studying'}
            <IconArrowRight />
          </button>
        ) : null}
      </div>
      {startError && <p role="alert" className="home__error">{startError}</p>}

      {/* the dock and captions are rendered by App */}
    </div>
  );
}
