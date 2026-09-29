# FRONTEND-020: «Цена ниже рынка» на странице объявления

## Контекст
Бэкенд (TASK-093): `GET /api/listings/{id}/price` (с `X-Telegram-Init-Data`):

```json
{"level": "below", "diff_percent": -17, "typical_price": 1200.0, "currency": "GEL",
 "sample": 7, "basis": "district_rooms", "premium_required": false}
```

`level`: `below` / `fair` / `above` / `unknown`. Без Premium `diff_percent`, `typical_price`,
`sample`, `basis` — `null`, а `premium_required: true`.

## Что сделать
1. Страница объявления, под ценой — плашка:
   - `below` — зелёная «Ниже рынка»; с Premium: «На 17% дешевле похожих в районе
     (обычно 1 200 ₾, по 7 объявлениям)».
   - `fair` — серая «Обычная цена для района».
   - `above` — оранжевая «Выше рынка» (с Premium — «на 12% дороже…»).
   - `unknown` — ничего не показывать.
2. `premium_required: true` — рядом ссылка «Насколько? — Premium» → `/premium`.
3. Вне Telegram (нет initData, ответ 401) — плашку не показывать.
4. `basis: "district_m2"` — в подсказке «по цене за м² в районе».
5. Тексты ka / ru / en.

## Проверка
- Premium видит проценты и обычную цену, бесплатный — только оценку и ссылку на Premium.
- `npx tsc --noEmit` и `npm run build` без ошибок.
