import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, type ReactNode } from 'react';
import { api, type LiveConnection } from '../api';
import type {
  Caption,
  ChatMessage,
  ClientEvent,
  MapNode,
  Material,
  ServerEvent,
  SessionSnapshot,
  SessionSummary,
  VoiceStatus,
} from '../types';
import { setLevel } from './level';

// ---------------- state ----------------

export type Screen = 'home' | 'study';

export interface AppState {
  screen: Screen;
  session: SessionSummary | null;
  materials: Material[];
  nodes: MapNode[];
  voice: VoiceStatus;
  captions: { user: Caption | null; assistant: Caption | null };
  messages: ChatMessage[];
  focusId: string | null;
  openNodeId: string | null;
  historyOpen: boolean;
  inputMode: 'voice' | 'text';
  drawerOpen: boolean;
  showUserCaptions: boolean;
  /** true right after leaving Home, so the material box plays its fly-to-corner animation */
  boxFlyIn: boolean;
  error: string | null;
}

const initialState: AppState = {
  screen: 'home',
  session: null,
  materials: [],
  nodes: [],
  voice: 'idle',
  captions: { user: null, assistant: null },
  messages: [],
  focusId: null,
  openNodeId: null,
  historyOpen: false,
  inputMode: 'voice',
  drawerOpen: false,
  showUserCaptions: true,
  boxFlyIn: false,
  error: null,
};

type Action =
  | { type: 'server'; event: ServerEvent }
  | { type: 'session.started'; session: SessionSummary; materials: Material[]; flyIn: boolean; nodes?: MapNode[]; messages?: ChatMessage[] }
  | { type: 'go.home' }
  | { type: 'ui.inputMode'; mode: 'voice' | 'text' }
  | { type: 'ui.drawer'; open: boolean }
  | { type: 'ui.openNode'; nodeId: string | null }
  | { type: 'ui.history'; open: boolean }
  | { type: 'ui.userCaptions'; show: boolean }
  | { type: 'ui.clearFocus' }
  | { type: 'local.caption'; caption: Caption }
  | { type: 'local.voice'; status: VoiceStatus }
  | { type: 'local.mapEdit'; op: 'rename' | 'remove' | 'add' | 'move'; nodeId: string; label?: string; parentId?: string; x?: number; y?: number };

function removeSubtree(nodes: MapNode[], id: string): MapNode[] {
  const doomed = new Set([id]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const n of nodes) {
      if (n.parentId && doomed.has(n.parentId) && !doomed.has(n.id)) {
        doomed.add(n.id);
        grew = true;
      }
    }
  }
  return nodes.filter((n) => !doomed.has(n.id));
}

function applyServer(state: AppState, e: ServerEvent): AppState {
  switch (e.type) {
    case 'voice.status':
      return { ...state, voice: e.status, error: e.status === 'thinking' ? null : state.error };
    case 'voice.level':
      return state; // handled outside the reducer (see level.ts)
    case 'caption':
      return { ...state, captions: { ...state.captions, [e.caption.role]: e.caption }, messages: e.message && !state.messages.some(item => item.id === e.message!.id) ? [...state.messages, e.message] : state.messages };
    case 'map.reset':
      return { ...state, nodes: e.nodes };
    case 'map.add': {
      const exists = state.nodes.some((n) => n.id === e.node.id);
      return {
        ...state,
        nodes: exists ? state.nodes.map((n) => (n.id === e.node.id ? e.node : n)) : [...state.nodes, e.node],
      };
    }
    case 'map.update':
      return { ...state, nodes: state.nodes.map((n) => (n.id === e.nodeId ? { ...n, ...e.patch } : n)) };
    case 'map.remove':
      return { ...state, nodes: removeSubtree(state.nodes, e.nodeId) };
    case 'map.focus':
      return { ...state, focusId: e.nodeId };
    case 'error':
      console.warn('[DysCover]', e.message);
      return { ...state, error: e.message };
  }
}

function reducer(state: AppState, a: Action): AppState {
  switch (a.type) {
    case 'server':
      return applyServer(state, a.event);
    case 'session.started':
      return {
        ...state,
        screen: 'study',
        session: a.session,
        materials: a.materials,
        nodes: a.nodes ?? [],
        captions: { user: null, assistant: null },
        messages: a.messages ?? [],
        openNodeId: null,
        historyOpen: false,
        drawerOpen: false,
        boxFlyIn: a.flyIn,
        error: null,
      };
    case 'go.home':
      return { ...initialState, showUserCaptions: state.showUserCaptions, inputMode: state.inputMode };
    case 'ui.inputMode':
      return { ...state, inputMode: a.mode };
    case 'ui.drawer':
      return { ...state, drawerOpen: a.open };
    case 'ui.openNode':
      return { ...state, openNodeId: a.nodeId, historyOpen: false, nodes: state.nodes.map((node) => node.id === a.nodeId && node.status === 'new' ? { ...node, status: 'normal' } : node) };
    case 'ui.history':
      return { ...state, historyOpen: a.open, openNodeId: a.open ? null : state.openNodeId };
    case 'ui.userCaptions':
      return { ...state, showUserCaptions: a.show };
    case 'ui.clearFocus':
      return { ...state, focusId: null };
    case 'local.caption':
      return { ...state, captions: { ...state.captions, [a.caption.role]: a.caption } };
    case 'local.voice':
      return { ...state, voice: a.status };
    case 'local.mapEdit':
      if (a.op === 'remove') return { ...state, nodes: removeSubtree(state.nodes, a.nodeId) };
      if (a.op === 'add') return { ...state, nodes: [...state.nodes, { id: a.nodeId, parentId: a.parentId ?? 'root', label: a.label ?? '', status: 'normal', userEdited: true, order: state.nodes.filter((node) => node.parentId === (a.parentId ?? 'root')).length }] };
      if (a.op === 'move') return { ...state, nodes: state.nodes.map((n) => n.id === a.nodeId ? { ...n, position: { x: a.x ?? 0, y: a.y ?? 0 } } : n) };
      return { ...state, nodes: state.nodes.map((n) => (n.id === a.nodeId ? { ...n, label: a.label ?? n.label, userEdited: true, status: 'normal', correction: null, pendingRemoval: null } : n)) };
  }
}

// ---------------- context ----------------

interface Store {
  state: AppState;
  dispatch: React.Dispatch<Action>;
  /** Send an event over the live connection (no-op when not connected). */
  send: (event: ClientEvent) => void;
  setInputMode: (mode: 'voice' | 'text') => void;
  startNewSession: (files: File[]) => Promise<void>;
  openPastSession: (sessionId: string) => Promise<void>;
  goHome: () => void;
}

const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const conn = useRef<LiveConnection | null>(null);
  const inputMode = useRef<'voice' | 'text'>('voice');

  const connect = useCallback((sessionId: string) => {
    conn.current?.close();
    conn.current = api.connect(sessionId, (event) => {
      if (event.type === 'voice.level') setLevel(event.level);
      else dispatch({ type: 'server', event });
    });
    conn.current.setInputMode(inputMode.current);
  }, []);

  useEffect(() => () => conn.current?.close(), []);

  const send = useCallback((event: ClientEvent) => conn.current?.send(event), []);
  const setInputMode = useCallback((mode: 'voice' | 'text') => {
    inputMode.current = mode;
    conn.current?.setInputMode(mode);
    if (mode === 'text' && state.voice === 'ended' && conn.current) {
      // Resume typed turns only after text mode has stopped microphone capture.
      conn.current.send({ type: 'session.resume' });
      dispatch({ type: 'local.voice', status: 'listening' });
    }
    dispatch({ type: 'ui.inputMode', mode });
  }, [state.voice]);

  const startNewSession = useCallback(
    async (files: File[]) => {
      const { session, materials } = await api.createSession(files);
      dispatch({ type: 'session.started', session, materials, flyIn: true });
      connect(session.id);
    },
    [connect],
  );

  const openPastSession = useCallback(
    async (sessionId: string) => {
      const snap: SessionSnapshot = await api.getSession(sessionId);
      dispatch({ type: 'session.started', session: snap.session, materials: snap.materials, nodes: snap.nodes, messages: snap.messages, flyIn: false });
      connect(snap.session.id);
    },
    [connect],
  );

  const goHome = useCallback(() => {
    conn.current?.close();
    conn.current = null;
    setLevel(0);
    dispatch({ type: 'go.home' });
  }, []);

  const value = useMemo(
    () => ({ state, dispatch, send, setInputMode, startNewSession, openPastSession, goHome }),
    [state, send, setInputMode, startNewSession, openPastSession, goHome],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore(): Store {
  const s = useContext(Ctx);
  if (!s) throw new Error('useStore must be used inside <StoreProvider>');
  return s;
}
