import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// During development, requests to /api are proxied to the backend.
// Change the target to wherever the backend runs.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
