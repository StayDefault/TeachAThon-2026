import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

function load(path, exported, hooks = {}) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8');
  const javascript = ts.transpileModule(`${source}\nexport { ${exported} };`, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const exports = {};
  const jsx = (type, props) => ({ type, props });
  const require = (name) => name === 'react'
    ? { createContext: () => ({}), useEffect() {}, ...hooks }
    : name === 'react/jsx-runtime' ? { jsx, jsxs: jsx } : {};
  new Function('require', 'exports', javascript)(require, exports);
  return exports[exported];
}

const reducer = load('../src/state/store.tsx', 'reducer');
const NodeBox = load('../src/components/map/ConceptMap.tsx', 'NodeBox');
const Legend = load('../src/components/map/ConceptMap.tsx', 'Legend');
const root = { id: 'root', parentId: null, label: 'Root', status: 'normal', order: 0 };
const child = { id: 'child', parentId: 'root', label: 'Child', status: 'new', order: 0 };
assert.equal(reducer({ nodes: [] }, { type: 'server', event: { type: 'voice.audio', sampleRate: 16000 } }).liveVoice, true);
let state = { nodes: [root, child], openNodeId: null };
const moved = reducer(state, { type: 'local.mapEdit', op: 'move', nodeId: 'child', x: 500, y: 200 });
assert.equal(moved.nodes[1].userEdited, undefined);
assert.equal(moved.nodes[1].status, 'new');
const text = (element) => element == null || typeof element === 'boolean' ? ''
  : typeof element === 'string' ? element
    : Array.isArray(element) ? element.map(text).join(' ') : text(element.props?.children);
const render = (node) => NodeBox({ box: { node, depth: 1, x: 0, y: 0, w: 250, h: 56 }, onOpen() {}, onMove() {} });
assert.deepEqual(Legend().props.children.map(item => text(item).trim()), ['Default', 'New', 'Edited', 'Corrected', 'Proposed removal']);

assert.match(text(render(child)), /New/);
state = reducer(state, { type: 'ui.openNode', nodeId: 'child' });
assert.equal(state.nodes[1].status, 'normal');
assert.doesNotMatch(text(render(state.nodes[1])), /New/);

state = reducer(state, { type: 'local.mapEdit', op: 'rename', nodeId: 'child', label: 'Edited child' });
assert.match(render(state.nodes[1]).props.className, /node--edited/);
assert.equal((text(render(state.nodes[1])).match(/Edited/g) ?? []).length, 2); // label plus one badge

state = reducer(state, { type: 'local.mapEdit', op: 'add', nodeId: 'own', parentId: 'root', label: 'Own idea' });
const added = state.nodes[2];
assert.equal(added.order, 1);
assert.match(render(added).props.className, /node--edited/);
assert.match(text(render(added)), /Edited/);
assert.doesNotMatch(text(render(added)), /New/);
const historyState = reducer(state, { type: 'ui.history', open: true });
assert.equal(historyState.openNodeId, null);
assert.equal(historyState.historyOpen, true);
assert.equal(reducer(historyState, { type: 'ui.openNode', nodeId: 'child' }).historyOpen, false);
const agreed = reducer(state, { type: 'server', event: { type: 'map.update', nodeId: 'child', patch: { userEdited: false, status: 'normal' } } });
assert.doesNotMatch(render(agreed.nodes[1]).props.className, /node--edited/);
const pending = { ...child, pendingRemoval: 'Duplicates another idea.' };
assert.match(render(pending).props.className, /node--removal/);
assert.match(text(render(pending)), /Review removal/);
assert.doesNotMatch(text(render(pending)), /New/);

const Captions = load('../src/components/Captions.tsx', 'Captions', { useState: () => [true, () => {}] });
const captionProps = { assistant: { text: 'Assistant words' }, user: { text: 'User words' }, showUser: true };
for (const status of ['speaking', 'listening']) {
  const line = Captions({ ...captionProps, status }).props.children;
  assert.equal(line.props.maxLines, 1);
  assert.equal(line.props.text, status === 'speaking' ? 'Assistant words' : 'User words');
}

let deleted = false, kept = false, expanded = false, learned = false, selectedBranch = null;
const detail = { title: 'Child', breadcrumb: [], summary: 'An idea.', messages: [] };
const NodePanel = load('../src/components/NodePanel.tsx', 'NodePanel', {
  useState: value => [value === null ? detail : value, () => {}],
});
const panel = NodePanel({ sessionId: 'test', nodeId: 'child', node: pending,
  childNodes: [{ ...child, id: 'sub', parentId: 'child', label: 'Subtopic' }],
  onExpand() { expanded = true; }, onLearn() { learned = true; }, onSelect(nodeId) { selectedBranch = nodeId; },
  onRemove() { deleted = true; }, onKeep() { kept = true; } });
const elements = element => !element || typeof element !== 'object' ? []
  : Array.isArray(element) ? element.flatMap(elements) : [element, ...elements(element.props?.children)];
let dockValues = [], dockHook = 0;
const sentTexts = [];
const VoiceDock = load('../src/components/VoiceDock.tsx', 'VoiceDock', {
  useState(initial) { const index = dockHook++; if (dockValues[index] === undefined) dockValues[index] = initial; return [dockValues[index], value => { dockValues[index] = value; }]; },
});
const drawDock = (status = 'thinking', mode = 'text') => {
  dockHook = 0;
  return VoiceDock({ status, mode, onModeChange() {}, onToggleSession() {}, onSendText(value) { sentTexts.push(value); } });
};
elements(drawDock()).find(element => element.type === 'input').props.onChange({ target: { value: '  Explain Java records  ' } });
elements(drawDock()).find(element => element.type === 'form').props.onSubmit({ preventDefault() {} });
assert.deepEqual(sentTexts, ['Explain Java records']);
assert.equal(elements(drawDock()).find(element => element.type === 'input').props.value, '');
for (const status of ['thinking', 'speaking', 'listening', 'ended']) {
  const receipt = elements(drawDock(status)).find(element => element.type === 'details');
  assert.match(text(receipt), /Explain Java records/);
  assert.equal(receipt.props['aria-live'], 'polite');
}
assert.equal(elements(drawDock('listening', 'voice')).some(element => element.type === 'details'), false);
const buttons = elements(panel).filter(element => element.type === 'button');
buttons.find(button => button.props['aria-label'] === 'Open subtopic Subtopic').props.onClick();
assert.equal(selectedBranch, 'sub');
assert.equal(expanded, false);
assert.equal(learned, false);
buttons.find(button => text(button) === 'Expand subtopics').props.onClick();
assert.equal(expanded, true);
buttons.find(button => text(button) === 'Learn this topic').props.onClick();
assert.equal(learned, true);
const expandedState = reducer({ ...state, openNodeId: null, historyOpen: true }, { type: 'server', event: { type: 'map.expanded', nodeId: 'root' } });
assert.equal(expandedState.openNodeId, 'root');
assert.equal(expandedState.historyOpen, false);
assert.equal(deleted, false);
buttons.find(button => text(button) === 'Keep node').props.onClick();
assert.equal(kept, true);
assert.equal(deleted, false);
buttons.find(button => text(button) === 'Confirm deletion').props.onClick();
assert.equal(deleted, true);
assert.doesNotMatch(text(panel), /OUR CONVERSATION/);
const ConversationHistory = load('../src/components/ConversationHistory.tsx', 'ConversationHistory', {
  useState: value => [Array.isArray(value) ? [{ id: 'one', role: 'user', text: 'First topic', at: '2026-10-24T10:00:00Z' }, { id: 'two', role: 'assistant', text: 'Second topic', at: '2026-10-24T10:00:01Z' }] : typeof value === 'boolean' ? false : value, () => {}],
});
const historyPanel = ConversationHistory({ sessionId: 'sample', revision: '', onClose() {} });
assert.match(text(historyPanel), /First topic/);
assert.match(text(historyPanel), /Second topic/);
const savedMessage = { id: 'persisted', role: 'assistant', text: 'Saved full reply', at: '2026-10-24T10:01:00Z' };
let messageState = { ...state, captions: { user: null, assistant: null }, messages: [] };
const captionEvent = { type: 'server', event: { type: 'caption', caption: { role: 'assistant', text: 'Saved', final: false }, message: savedMessage } };
messageState = reducer(messageState, captionEvent);
messageState = reducer(messageState, captionEvent);
assert.deepEqual(messageState.messages, [savedMessage]);
const updatedMessage = { ...savedMessage, text: 'Saved full reply with another transcript fragment' };
messageState = reducer(messageState, { type: 'server', event: { type: 'caption', caption: { role: 'assistant', text: updatedMessage.text, final: false }, message: updatedMessage } });
assert.deepEqual(messageState.messages, [updatedMessage]);
const liveHistory = ConversationHistory({ sessionId: 'sample', liveMessages: messageState.messages, onClose() {} });
assert.match(text(liveHistory), /Saved full reply/);

const oldWindow = globalThis.window;
let hookValues = [], hookIndex = 0, effects = [], timers = [];
globalThis.window = { setTimeout(fn, delay) { timers.push({ fn, delay }); return timers.length; }, clearTimeout() {} };
try {
  const TimedCaptions = load('../src/components/Captions.tsx', 'Captions', {
    useState(initial) { const index = hookIndex++; if (hookValues[index] === undefined) hookValues[index] = initial; return [hookValues[index], value => { hookValues[index] = value; }]; },
    useEffect(fn) { effects.push(fn); },
  });
  const props = { assistant: { text: 'A spoken answer', final: true }, user: null, showUser: false };
  const draw = status => { hookIndex = 0; effects = []; const tree = TimedCaptions({ ...props, status }); return tree; };
  draw('speaking'); effects.forEach(fn => fn());
  assert.equal(timers.length, 0);
  assert.equal(draw('speaking').props.children.props.text, 'A spoken answer');
  draw('listening'); effects.forEach(fn => fn());
  assert.equal(timers.length, 0);
  assert.equal(draw('listening').props.children.props.text, 'A spoken answer');
} finally { globalThis.window = oldWindow; }
console.log('Node marker checks passed.');
