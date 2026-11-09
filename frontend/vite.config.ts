import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// GitHub Pages отдаёт сайт из подпапки /real-estate-rental/, поэтому base нужен только для сборки.
// Dev: Vite (5173) работает от корня и проксирует /api на локальный FastAPI (порт 8000).
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/real-estate-rental/' : '/',
  plugins: [react(), tailwindcss()],
  build: {
    rolldownOptions: {
      output: {
        // Первый запуск Mini App (FRONTEND-050): всё, что нужно сразу, — в двух файлах
        // (библиотеки и наш код), а не в десятке мелких; редкие страницы — отдельными частями
        codeSplitting: {
          groups: [
            { name: 'vendor', test: /node_modules[\/]/, tags: ['$initial'], priority: 2 },
            { name: 'app', tags: ['$initial'], priority: 1 },
          ],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
}));
