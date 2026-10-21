import type {
  ClientEvent,
  Material,
  NodeDetail,
  ServerEvent,
  SessionSnapshot,
  SessionSummary,
} from '../types';

/**
 * The ONLY surface the UI uses to talk to the backend.
 * Two implementations exist:
 *   - mock.ts  — scripted demo, no server needed (default)
 *   - http.ts  — real REST + WebSocket client (fill in the TODOs)
 * Pick one with VITE_USE_MOCK in .env (see api/index.ts).
 */
export interface DysCoverBackend {
  /** Upload the learner's files and create a new study session. */
  createSession(files: File[]): Promise<{ session: SessionSummary; materials: Material[] }>;

  /** Past sessions for the sidebar, newest first. */
  listSessions(): Promise<SessionSummary[]>;

  /** Everything needed to reopen a past session. */
  getSession(sessionId: string): Promise<SessionSnapshot>;

  /** Content of the quarter-screen panel when a node is clicked. */
  getNodeDetail(sessionId: string, nodeId: string): Promise<NodeDetail>;

  /**
   * Open the live, always-on voice connection for a session.
   * The backend streams ServerEvents; the UI sends ClientEvents.
   * Audio capture / playback lives inside the implementation, not in the UI.
   */
  connect(sessionId: string, onEvent: (event: ServerEvent) => void): LiveConnection;
}

export interface LiveConnection {
  send(event: ClientEvent): void;
  close(): void;
}
