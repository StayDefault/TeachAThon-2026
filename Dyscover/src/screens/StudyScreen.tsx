import { useCallback } from 'react';
import { useStore } from '../state/store';
import { ConceptMap } from '../components/map/ConceptMap';
import { MaterialBox } from '../components/MaterialBox';
import { NodePanel } from '../components/NodePanel';
import { IconChart, IconChat } from '../components/Icons';
import './StudyScreen.css';

/** Study: the map grows while the learner talks with the voice model. */
export function StudyScreen() {
  const { state, dispatch, send } = useStore();
  const { session, materials, nodes, choices, focusId, openNodeId, boxFlyIn } = state;

  const openNode = useCallback(
    (nodeId: string) => {
      dispatch({ type: 'ui.openNode', nodeId });
      send({ type: 'user.node_opened', nodeId });
    },
    [dispatch, send],
  );
  const clearFocus = useCallback(() => dispatch({ type: 'ui.clearFocus' }), [dispatch]);

  if (!session) return null;

  return (
    <div className="study">
      <MaterialBox title={session.title} materials={materials} flyIn={boxFlyIn} />

      <ConceptMap nodes={nodes} focusId={focusId} selectedId={openNodeId} onOpen={openNode} onFocusDone={clearFocus} />

      {choices.length > 0 && (
        <div className="choices">
          {choices.map((c, i) => (
            <button
              key={c.id}
              className="choice"
              style={{ animationDelay: `${i * 90}ms` }}
              onClick={() => {
                dispatch({ type: 'server', event: { type: 'prompt.clear' } });
                send({ type: 'user.choice', choiceId: c.id });
              }}
            >
              <span className="choice__icon" aria-hidden="true">
                {i === 0 ? <IconChart size={22} /> : <IconChat size={22} />}
              </span>
              <span className="choice__text">
                <span className="choice__title">{c.title}</span>
                {c.subtitle && <span className="choice__sub">{c.subtitle}</span>}
              </span>
            </button>
          ))}
        </div>
      )}

      {openNodeId && (
        <NodePanel sessionId={session.id} nodeId={openNodeId} onClose={() => dispatch({ type: 'ui.openNode', nodeId: null })} />
      )}
    </div>
  );
}
