/**
 * API configuration — zero hardcoded hosts.
 *
 * Resolution order:
 *   1. Vite env var  VITE_API_BASE   (e.g. https://aegis.mha.gov.in)
 *   2. Same origin   (production: frontend served by FastAPI on :8000)
 *   3. Dev fallback  http://127.0.0.1:8000 when running under the Vite dev server
 */

const DEV_FALLBACK = 'http://127.0.0.1:8000';
const isViteDev = typeof window !== 'undefined' && window.location.port === '5173';

function resolveBase() {
  // 1. Build-time override via .env / .env.production
  // eslint-disable-next-line no-undef
  const envBase = typeof import.meta !== 'undefined' && import.meta.env
    ? import.meta.env.VITE_API_BASE
    : undefined;
  if (envBase) return envBase.replace(/\/$/, '');
  // 2. Same-origin (docker/prod deployment)
  if (!isViteDev && typeof window !== 'undefined') return '';
  // 3. Vite dev server -> backend on default port
  return DEV_FALLBACK;
}

export const API_BASE = resolveBase();

export const apiUrl = (path) => `${API_BASE}${path}`;

export const getWebSocketUrl = (path) => {
  const base = API_BASE || (typeof window !== 'undefined' ? window.location.origin : '');
  const protocol = base.startsWith('https') || base.startsWith('wss')
    ? 'wss:'
    : (typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:');
  const hostPart = base.replace(/^https?:\/\//, '').replace(/^wss?:\/\//, '');
  return `${protocol}//${hostPart}${path}`;
};
