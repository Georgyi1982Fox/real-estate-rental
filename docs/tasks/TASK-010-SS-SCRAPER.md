# TASK-010: Парсер SS.ge

## Цель
Второй источник объявлений: аренда квартир в Тбилиси с SS.ge (пункт 006 в `tasks_structure.md`).

## Требования

### 1. Адрес поиска
SS.ge переехал на `home.ss.ge`, старый адрес `ss.ge/ru/le/...` не работает.
- `SSSettings.SEARCH_PATH`: `/ru/недвижимость/l/Квартира/Аренда?currencyId=1&page={page}`
  (переопределяется `SS_SEARCH_PATH`), `SS_MAX_PAGES` (по умолчанию 20).
- Город в адресе не задаётся: в выдаче есть Батуми и другие города. Парсер оставляет
  только города из `SCRAPE_CITIES` (`address.cityId`: 95 — Тбилиси, 96 — Батуми; TASK-079).

### 2. Разбор страницы
Сайт на Next.js: 16 объявлений на странице лежат JSON-ом в `__NEXT_DATA__`
(`props.pageProps.applicationList.realStateItemModel`). Общий код чтения JSON:
`src/bina/infrastructure/scrapers/nextjs.py` (им пользуется и MyHome).

| Поле `RawListing` | JSON SS.ge |
|---|---|
| `source_id` | `applicationId` |
| `title` / `description` | `title` / `description` (полное описание, страницы объявлений не нужны) |
| `price`, `currency` | `price.priceGeo`, всегда GEL |
| `rooms` | из заголовка (`2-комнатная`), иначе `numberOfBedrooms + 1` |
| `area` | `totalArea` |
| `district` | `address.subdistrictTitle` (Ваке, Сабуртало — как у MyHome) |
| `photos` | `appImages[].fileName`, главное первым |
| `url` | `https://home.ss.ge/ru/недвижимость/{detailUrl}` |

Телефона и имени владельца в JSON списка нет. Разбор HTML по селекторам остался запасным вариантом.

### 3. Надёжность
- Ошибка страницы пропускается, после 3 подряд парсинг останавливается.
- Остановка, если страница не принесла новых ID (защита от сайта, игнорирующего `page`).
  Страница только с другими городами концом выдачи не считается.
- `bina-scrape --source ss --dump-dir DIR` сохраняет `ss_list.html`.

### 4. Тесты
`tests/unit/infrastructure/scrapers/test_ss_scraper.py`: урезанная копия настоящей страницы
(`test_data/ss_next_list.html`: 2 объявления в Тбилиси и 1 в Батуми), пагинация, лимит, ошибки,
фильтр города. Старый тест, ходивший в сеть, заменён.

## Запуск
```bash
bina-scrape --source ss --limit 100
bina-scrape --source all --limit 100   # MyHome и SS.ge
```

Автозапуск (пункт 008): оба сайта сразу и затем каждые `--interval` часов
(по умолчанию `SCRAPE_INTERVAL_HOURS`, 6). После каждого запуска печатается итог;
ошибка одного запуска не останавливает расписание. Работает, пока открыто окно.
```bash
bina-scrape schedule --interval 6 --limit 100
```

## Definition of Done
1. ✅ Объявления SS.ge разбираются с настоящей страницы
2. ✅ Только Тбилиси
3. ✅ Тесты, ruff и mypy для нового кода
4. ⏳ Проверка `bina-scrape --source ss` на машине с доступом к сайту
