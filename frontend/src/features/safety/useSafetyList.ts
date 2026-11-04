import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";

type Paged<T> = { total: number; items: T[] };
const PAGE = 25;

/** Loads a vehicle's recalls/complaints/TSBs with filter + "show more" paging. */
export function useSafetyList<T, L extends Paged<T>>(vehicleId: string, kind: string, q: string) {
  const { t } = useTranslation();
  const [data, setData] = useState<L | null>(null);
  const [items, setItems] = useState<T[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(
    async (offset: number, signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
        if (q.trim()) params.set("q", q.trim());
        const res = await api<L>(`/vehicles/${vehicleId}/${kind}?${params}`, { signal });
        setData(res);
        setItems((prev) => (offset === 0 ? res.items : [...prev, ...res.items]));
      } catch (e) {
        if ((e as Error).name !== "AbortError") setError(errorMessage(t, e));
      } finally {
        setLoading(false);
      }
    },
    [vehicleId, kind, q, t],
  );

  useEffect(() => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => void load(0, ctrl.signal), q ? 300 : 0);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [load, q]);

  return { data, items, error, loading, more: () => load(items.length), hasMore: !!data && items.length < data.total };
}
