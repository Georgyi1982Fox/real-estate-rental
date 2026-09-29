# TASK-093: Анализ цены — дешевле или дороже обычного

## Что делает
`GET /api/listings/{id}/price` (нужен `X-Telegram-Init-Data`) сравнивает цену объявления с
похожими квартирами района:

1. **Те же комнаты в том же районе** (4 и больше — одна группа): медиана цены, если таких
   объявлений хотя бы 5.
2. Иначе **цена за м² района**, умноженная на площадь (тоже от 5 объявлений).
3. Иначе `unknown` — сравнивать не с чем.

В сравнении только то, что видит пользователь: активные, не скрытые антифродом, без скрытых
дубликатов. Валюта та же (всё в лари после нормализации).

| `level` | Когда |
|---|---|
| `below` | дешевле обычного больше чем на 10% |
| `fair` | в пределах ±10% |
| `above` | дороже больше чем на 10% |
| `unknown` | мало данных |

## Бесплатно и Premium
- Бесплатно: только `level` и `premium_required: true` («Узнать насколько — Premium»).
- Premium: `diff_percent` (−17 — на 17% дешевле), `typical_price` (обычная цена такой
  квартиры), `sample` (сколько объявлений в сравнении), `basis`.

```json
{"level": "below", "diff_percent": -17, "typical_price": 1200.0, "currency": "GEL",
 "sample": 7, "basis": "district_rooms", "premium_required": false}
```

## Код
`application/price_analysis.py` (полоса ±10%, группы комнат), `use_cases/analyze_price.py`,
`ListingsRepository.rooms_median_price` / `district_price_per_m2`.

## Фронтенд
`FRONTEND-020-PRICE-BADGE.md` (не выдана).
