import type { LessonProgress as Progress, LessonState } from '../types';
import './LessonProgress.css';

const LABEL: Record<LessonState, string> = {
  unseen: 'not started',
  introduced: 'explained',
  attempted: 'tried',
  understood: 'understood',
  review: 'to review',
  skipped: 'skipped',
};

/** One step per lesson concept; pressing a step asks the tutor to teach it. */
export function LessonProgress({ lesson, onLearn }: { lesson: Progress; onLearn: (planId: string) => void }) {
  if (!lesson.items.length) return null;
  const understood = lesson.items.filter((item) => item.state === 'understood').length;
  const focus = lesson.items.find((item) => item.id === lesson.focusId);
  return (
    <nav className="lesson" aria-label="Lesson progress">
      <span className="lesson__count">{understood} of {lesson.items.length} understood</span>
      <ol className="lesson__steps">
        {lesson.items.map((item) => (
          <li key={item.id}>
            <button
              className={`lesson__step lesson__step--${item.state} ${item.id === lesson.focusId ? 'lesson__step--focus' : ''}`}
              onClick={() => onLearn(item.id)}
              title={item.title}
              aria-label={`${item.title}, ${LABEL[item.state]}${item.id === lesson.focusId ? ', studying now' : ''}. Study this concept`}
            >
              <span aria-hidden="true" />
            </button>
          </li>
        ))}
      </ol>
      {focus && <span className="lesson__focus">Now: {focus.title}</span>}
    </nav>
  );
}
