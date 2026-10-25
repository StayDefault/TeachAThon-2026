import { useCallback, useEffect } from 'react';
import { useStore } from '../state/store';
import { ConceptMap } from '../components/map/ConceptMap';
import { MaterialBox } from '../components/MaterialBox';
import { NodePanel } from '../components/NodePanel';
import { ConversationHistory } from '../components/ConversationHistory';
import './StudyScreen.css';

/** Study: the map grows while the learner talks with the voice model. */
export function StudyScreen() {
  const { state, dispatch, send } = useStore();
  const { session, materials, nodes, edges, focusId, openNodeId, boxFlyIn } = state;
  useEffect(() => {
    send({ type: 'user.node_opened', nodeId: openNodeId ?? '' });
  }, [openNodeId, send]);

  const openNode = useCallback(
    (nodeId: string) => {
      dispatch({ type: 'ui.openNode', nodeId });
      if (nodes.some((node) => node.id === nodeId && node.status === 'new')) {
        send({ type: 'user.map_edit', op: 'acknowledge', nodeId });
      }
    },
    [dispatch, nodes, send],
  );
  const clearFocus = useCallback(() => dispatch({ type: 'ui.clearFocus' }), [dispatch]);

  if (!session) return null;

  return (
    <div className="study">
      <MaterialBox sessionId={session.id} title={session.title} materials={materials} flyIn={boxFlyIn} />

      <ConceptMap sessionId={session.id} nodes={nodes} edges={edges} focusId={focusId} selectedId={openNodeId} onOpen={openNode} onFocusDone={clearFocus}
        onMove={(nodeId, x, y) => { dispatch({ type: 'local.mapEdit', op: 'move', nodeId, x, y }); send({ type: 'user.map_edit', op: 'move', nodeId, x, y }); }} />

      {openNodeId && (
        <NodePanel sessionId={session.id} nodeId={openNodeId} node={nodes.find((node) => node.id === openNodeId)} pendingAction={state.pendingAction} onClose={() => dispatch({ type: 'ui.openNode', nodeId: null })}
          childNodes={nodes.filter(node => node.parentId === openNodeId)}
          onSelect={openNode}
          onExpand={() => { dispatch({ type: 'ui.pendingAction', action: 'expand' }); send({ type: 'user.action', action: 'expand', nodeId: openNodeId }); }}
          onLearn={() => { dispatch({ type: 'ui.pendingAction', action: 'learn' }); send({ type: 'user.action', action: 'learn', nodeId: openNodeId }); }}
          onKeep={() => send({ type: 'user.map_edit', op: 'keep', nodeId: openNodeId })}
          onRemove={() => { send({ type: 'user.map_edit', op: 'remove', nodeId: openNodeId }); dispatch({ type: 'local.mapEdit', op: 'remove', nodeId: openNodeId }); dispatch({ type: 'ui.openNode', nodeId: null }); }} />
      )}
      {state.historyOpen && <ConversationHistory sessionId={session.id}
        liveMessages={state.messages}
        onClose={() => dispatch({ type: 'ui.history', open: false })} />}
    </div>
  );
}
