import { defineConfig } from 'vite';
import type { Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

/**
 * Словари ru / en — отдельные части (FRONTEND-054). Чтобы человек с ru / en не ждал лишний
 * круг по сети, маленький скрипт в начале index.html сразу начинает скачивать словарь его
 * языка — параллельно с основной частью. Язык — как в I18nProvider: ?lang= → bina_lang
 */
function preloadLanguage(): Plugin {
  let base = '/';
  return {
    name: 'bina-preload-language',
    apply: 'build',
    configResolved(config) {
      base = config.base;
    },
    transformIndexHtml: {
      order: 'post',
      handler(html, ctx) {
        const files: Record<string, string> = {};
        for (const chunk of Object.values(ctx.bundle ?? {})) {
          if (chunk.type !== 'chunk') continue;
          const lang = chunk.facadeModuleId?.match(/\/src\/i18n\/(ru|en)\.ts$/)?.[1];
          if (lang) files[lang] = base + chunk.fileName;
        }
        const script =
          `(function(){var f=${JSON.stringify(files)},l=new URLSearchParams(location.search).get('lang');` +
          `try{if(!f[l])l=localStorage.getItem('bina_lang')}catch(e){}` +
          `if(f[l]){var e=document.createElement('link');e.rel='modulepreload';e.crossOrigin='';e.href=f[l];document.head.appendChild(e)}})()`;
        return html.replace(
          '<head>',
          `<head>
    <script>${script}</script>`,
        );
      },
    },
  };
}

// GitHub Pages отдаёт сайт из подпапки /real-estate-rental/, поэтому base нужен только для сборки.
// Dev: Vite (5173) работает от корня и проксирует /api на локальный FastAPI (порт 8000).
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/real-estate-rental/' : '/',
  plugins: [react(), tailwindcss(), preloadLanguage()],
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
