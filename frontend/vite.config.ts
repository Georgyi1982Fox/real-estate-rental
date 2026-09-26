import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// GitHub Pages отдаёт сайт из подпапки /real-estate-rental/, поэтому base нужен только для сборки.
// Dev: Vite (5173) работает от корня и проксирует /api на локальный FastAPI (порт 8000).
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/real-estate-rental/' : '/',
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
}));
