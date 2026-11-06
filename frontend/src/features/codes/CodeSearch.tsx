import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { Alert, Button, Input, Label } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import type { DtcSummary } from "../../lib/types";

export const CODE_RE = /^[PBCU][0-3][0-9A-F]{3}$/;
export const normalizeCode = (s: string) => s.replace(/[\s-]/g, "").toUpperCase();

export const SEVERITY_STYLE = {
  low: "bg-slate-200 text-slate-900 dark:bg-slate-700 dark:text-slate-50",
  medium: "bg-amber-400 text-slate-950",
  high: "bg-red-700 text-white",
} as const;

export default function CodeSearch({ autoFocus = false }: { autoFocus?: boolean }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<DtcSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      api<DtcSummary[]>(`/dtcs?q=${encodeURIComponent(q.trim())}&limit=40`, { signal: ctrl.signal })
        .then((r) => {
          setResults(r);
          setError(null);
        })
        .catch((e) => e.name !== "AbortError" && setError(errorMessage(t, e)));
    }, 200);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [q, t]);

  const code = normalizeCode(q);
  function submit(e: FormEvent) {
    e.preventDefault();
    if (CODE_RE.test(code)) navigate(`/codes/${code}`);
    else if (results?.length) navigate(`/codes/${results[0].code}`);
  }

  return (
    <div className="space-y-4">
      <form onSubmit={submit} className="space-y-3">
        <Label htmlFor="code-q">{t("codes.searchLabel")}</Label>
        <Input
          id="code-q"
          type="search"
          value={q}
          autoFocus={autoFocus}
          autoCapitalize="characters"
          autoCorrect="off"
          spellCheck={false}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("codes.searchPlaceholder")}
          className="font-mono text-xl"
        />
        {CODE_RE.test(code) && (
          <Button type="submit" className="w-full">
            {t("codes.lookUp", { code })}
          </Button>
        )}
      </form>
      {error && <Alert>{error}</Alert>}
      {!q && !!results?.length && <h2 className="text-xl font-bold">{t("codes.common")}</h2>}
      {results?.length === 0 && !CODE_RE.test(code) && <p>{t("codes.noResults")}</p>}
      <ul className="divide-y-2 divide-slate-200 dark:divide-slate-800">
        {results?.map((d) => (
          <li key={d.code}>
            <Link to={`/codes/${d.code}`} className="flex min-h-16 items-center gap-3 py-2">
              <span className="w-20 shrink-0 font-mono text-lg font-bold">{d.code}</span>
              <span className="flex-1 text-lg">{d.title}</span>
              <span className={`size-3 shrink-0 rounded-full ${SEVERITY_STYLE[d.severity]}`} aria-label={t(`codes.severity.${d.severity}`)} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
