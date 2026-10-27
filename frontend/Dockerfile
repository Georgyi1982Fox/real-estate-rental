# Сайт Mini App для туннеля (TASK-123): собранная версия вместо режима разработки.
# `npm run dev` отдаёт ~250 несжатых файлов (9 МБ) и Telegram перепроверяет их при каждом
# открытии; собранный сайт — ~20 файлов (0,5 МБ), а браузер Telegram кэширует их надолго.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Сайт — от корня домена (на GitHub Pages он в подпапке, там base свой)
RUN npx vite build --base /

# nginx отдаёт файлы сайта и пересылает /api в контейнер api
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
