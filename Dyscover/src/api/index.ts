import type { DysCoverBackend } from './backend';
import { createHttpBackend } from './http';
import { createMockBackend } from './mock';

const useMock = import.meta.env.VITE_USE_MOCK !== 'false';

/** The app-wide backend. Mock by default; set VITE_USE_MOCK=false to use the real server. */
export const api: DysCoverBackend = useMock
  ? createMockBackend()
  : createHttpBackend(import.meta.env.VITE_API_BASE || '');

export const isMock = useMock;
export type { DysCoverBackend, LiveConnection } from './backend';
