import { defineConfig } from 'vitest/config';

// Автотесты фронтенда (FRONTEND-057): `npm test`. Без браузера — проверяется логика
// и словари, а не страницы
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
