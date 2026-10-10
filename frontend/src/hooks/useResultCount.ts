import { useEffect, useState } from 'react';
import { useApi } from './useApi';

/** Пауза после изменения фильтра перед подсчётом */
const COUNT_DELAY_MS = 400;

/**
 * «Показать N …» в окне фильтров: сколько объектов найдётся по черновику фильтров.
 * Считаем не на каждое нажатие, а после паузы; при открытии окна — сразу.
 *
 * query — строка запроса черновика; pathFor строит адрес списка, который отвечает
 * { total } (например, /api/listings?per_page=1&…). total: undefined — ещё считаем
 */
export function useResultCount(
  open: boolean,
  query: string,
  pathFor: (query: string) => string,
): { counting: boolean; total: number | undefined } {
  // Запрос, для которого считаем; null — окно закрыто
  const [countQuery, setCountQuery] = useState<string | null>(null);
  const [wasOpen, setWasOpen] = useState(open);

  if (open !== wasOpen) {
    setWasOpen(open);
    if (!open) setCountQuery(null);
  }

  useEffect(() => {
    if (!open || query === countQuery) return;
    const timer = window.setTimeout(
      () => setCountQuery(query),
      countQuery === null ? 0 : COUNT_DELAY_MS,
    );
    return () => window.clearTimeout(timer);
  }, [open, query, countQuery]);

  const { data, error } = useApi<{ total: number }>(
    countQuery === null ? null : pathFor(countQuery),
  );
  const counting = countQuery !== query || (!data && !error);

  return { counting, total: counting ? undefined : data?.total };
}
