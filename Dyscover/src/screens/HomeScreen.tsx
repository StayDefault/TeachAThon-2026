import { useRef, useState, type DragEvent } from 'react';
import { useStore } from '../state/store';
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
  const boardRef = useRef<HTMLDivElement>(null);
  const boxRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [cards, setCards] = useState<Card[]>([]);
  const [files, setFiles] = useState<{ id: number; file: File }[]>([]);
  const [gulp, setGulp] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState('');
  const [fileListOpen, setFileListOpen] = useState(false);

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
    setFiles((f) => [...f, ...spawn.map(({ id, file }) => ({ id, file }))]);
    setStartError('');
  };

  const onLanded = (id: number) => {
    setCards((cs) => cs.filter((c) => c.id !== id));
    setGulp((g) => g + 1);
  };

  const removeFile = (id: number) => {
    setFiles((f) => f.filter((item) => item.id !== id));
    setCards((cs) => cs.filter((card) => card.id !== id));
    setStartError('');
    if (files.length === 1) setFileListOpen(false);
    boxRef.current?.focus();
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
      await startNewSession(files.map(({ file }) => file));
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

      <button ref={boxRef} type="button" className="home__box" key={gulp} data-gulp={gulp > 0}
        aria-label={files.length ? `Study box: manage ${files.length} selected files` : 'Add study files'}
        aria-expanded={files.length ? fileListOpen : undefined} aria-controls={files.length ? 'home-file-list' : undefined}
        onClick={() => files.length ? setFileListOpen((open) => !open) : inputRef.current?.click()}>
        <IconBox size={36} />
        <span className={inBox > 0 ? 'home__count' : 'home__drop'}>
          {inBox > 0 ? `${inBox} ${inBox === 1 ? 'file' : 'files'} · View` : dragOver ? 'Drop to add' : 'Click or drop to add'}
        </span>
      </button>
      <p className="home__boxlabel">Your study box</p>
      {fileListOpen && files.length > 0 && (
        <div id="home-file-list" className="home__filelist" aria-label="Selected study files">
          <div className="home__filelist-head">
            <strong>Selected files</strong>
            <button type="button" onClick={() => { setFileListOpen(false); boxRef.current?.focus(); }} aria-label="Close selected files">Close</button>
          </div>
          <ul className="home__files">
            {files.map(({ id, file }) => (
              <li key={id}>
                <span title={file.name}>{file.name}</span>
                <button type="button" onClick={() => removeFile(id)} disabled={starting} aria-label={`Remove ${file.name}`}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
          <button className="home__filelist-add" type="button" onClick={() => inputRef.current?.click()} disabled={starting}>
            Add files
          </button>
        </div>
      )}

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
        {startError && <p role="alert" className="home__error">{startError}</p>}
      </div>

      {!startError && <ol className="home__guide" aria-label="How DysCover works">
        <li><span>01</span><strong>Add your materials</strong><p>Bring your notes, slides, or a photo.</p></li>
        <li><span>02</span><strong>Talk it through</strong><p>Explore the ideas in conversation.</p></li>
        <li><span>03</span><strong>Build your map</strong><p>See how the concepts connect.</p></li>
      </ol>}

    </div>
  );
}
