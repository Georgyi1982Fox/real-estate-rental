import { useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

export type UrlChange = (params: URLSearchParams) => void;

/**
 * Параметры адреса страницы и их изменение. setSearchParams из React Router кодирует
 * запятую как %2C, а списки в адресе должны читаться: ?district=vake,saburtalo.
 *
 * update(change, replace, keepScroll): replace — без новой записи истории;
 * keepScroll — страница остаётся на месте (иначе ScrollRestoration прокрутит её наверх)
 */
export function useUrlParams() {
  const { search } = useLocation();
  const navigate = useNavigate();

  const update = useCallback(
    (change: UrlChange, replace: boolean, keepScroll = false) => {
      const params = new URLSearchParams(search);
      change(params);
      const next = params.toString().replace(/%2C/gi, ',');
      navigate({ search: next ? `?${next}` : '' }, { replace, preventScrollReset: keepScroll });
    },
    [search, navigate],
  );

  return { search, update };
}
