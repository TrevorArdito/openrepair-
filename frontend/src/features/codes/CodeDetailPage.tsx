import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { Alert, Button, Card, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { load, save } from "../../lib/storage";
import type { Dtc } from "../../lib/types";
import { useDocumentTitle } from "../../lib/title";
import { SEVERITY_STYLE } from "./CodeSearch";

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <Card>
      <h2 className="mb-2 text-xl font-bold">{title}</h2>
      <ul className="list-disc space-y-1 pl-6 text-lg">
        {items.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>
    </Card>
  );
}

function Checklist({ code, steps }: { code: string; steps: string[] }) {
  const { t } = useTranslation();
  const key = `cc.dtcChecklist.${code}`;
  const [done, setDone] = useState<number[]>(() => load<number[]>(key, []));
  const toggle = (i: number) => {
    const next = done.includes(i) ? done.filter((x) => x !== i) : [...done, i];
    setDone(next);
    save(key, next);
  };
  return (
    <Card>
      <h2 className="text-xl font-bold">{t("codes.steps")}</h2>
      <p className="mb-3 text-base text-slate-600 dark:text-slate-400">{t("codes.stepsHelp")}</p>
      <ol className="space-y-2">
        {steps.map((s, i) => {
          const checked = done.includes(i);
          return (
            <li key={s}>
              <button
                type="button"
                role="checkbox"
                aria-checked={checked}
                onClick={() => toggle(i)}
                className={`flex min-h-14 w-full items-start gap-3 rounded-xl border-2 p-3 text-left text-lg ${
                  checked ? "border-green-600 bg-green-50 dark:bg-green-950" : "border-slate-300 dark:border-slate-700"
                }`}
              >
                <span
                  className={`flex size-8 shrink-0 items-center justify-center rounded-full border-2 font-bold ${
                    checked ? "border-green-600 bg-green-600 text-white" : "border-slate-400"
                  }`}
                  aria-hidden="true"
                >
                  {checked ? "✓" : i + 1}
                </span>
                <span className={checked ? "line-through opacity-70" : ""}>{s}</span>
              </button>
            </li>
          );
        })}
      </ol>
      {done.length > 0 && (
        <Button variant="secondary" className="mt-3 w-full" onClick={() => { setDone([]); save(key, []); }}>
          {t("codes.reset")}
        </Button>
      )}
    </Card>
  );
}

export default function CodeDetailPage() {
  const { t } = useTranslation();
  const { code = "" } = useParams();
  const [dtc, setDtc] = useState<Dtc | null>(null);
  const [error, setError] = useState<string | null>(null);
  useDocumentTitle(dtc ? `${dtc.code}${dtc.title ? `: ${dtc.title}` : ""}` : code);

  useEffect(() => {
    setDtc(null);
    setError(null);
    api<Dtc>(`/dtcs/${encodeURIComponent(code)}`)
      .then(setDtc)
      .catch((e) => setError(errorMessage(t, e)));
  }, [code, t]);

  if (error)
    return (
      <div className="space-y-4">
        <Alert>{error}</Alert>
        <Link to="/codes" className="font-bold underline">{t("codes.title")}</Link>
      </div>
    );
  if (!dtc) return <Spinner label={t("app.loading")} />;

  const s = dtc.structure;
  return (
    <div className="space-y-4">
      <div>
        <p className="font-mono text-3xl font-extrabold text-amber-700 dark:text-amber-400">{dtc.code}</p>
        <PageTitle>{dtc.known ? dtc.title : t("codes.unknownTitle", { code: dtc.code })}</PageTitle>
        {dtc.severity && (
          <span className={`inline-block rounded-lg px-3 py-2 text-lg font-bold ${SEVERITY_STYLE[dtc.severity]}`}>
            {t(`codes.severity.${dtc.severity}`)}
          </span>
        )}
      </div>

      {dtc.known ? (
        <>
          <Card>
            <h2 className="mb-2 text-xl font-bold">{t("codes.meaning")}</h2>
            <p className="text-lg">{dtc.description}</p>
          </Card>
          <List title={t("codes.symptoms")} items={dtc.symptoms} />
          <List title={t("codes.causes")} items={dtc.causes} />
          <Checklist code={dtc.code} steps={dtc.diagnostic_steps} />
        </>
      ) : (
        <Alert kind="info">{t("codes.unknownBody")}</Alert>
      )}

      <Card>
        <h2 className="mb-2 text-xl font-bold">{t("codes.structureTitle")}</h2>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-lg">
          <dt className="font-semibold">{t("codes.systemLabel")}</dt>
          <dd>{t(`codes.system.${s.system}`)}</dd>
          <dt className="font-semibold">{t("codes.typeLabel")}</dt>
          <dd>{s.generic ? t("codes.generic") : t("codes.manufacturer")}</dd>
          {s.subsystem && (
            <>
              <dt className="font-semibold">{t("codes.subsystemLabel")}</dt>
              <dd>{t(`codes.subsystem.${s.subsystem}`)}</dd>
            </>
          )}
        </dl>
      </Card>

      <Card>
        <h2 className="mb-2 text-xl font-bold">{t("codes.related")}</h2>
        {dtc.related_entries.length === 0 ? (
          <p>{t("codes.noRelated")}</p>
        ) : (
          <ul>
            {dtc.related_entries.map((e) => (
              <li key={e.id}>
                <Link to={`/entries/${e.id}`} className="flex min-h-12 items-center font-semibold underline">
                  {e.title}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Alert kind="warning">{t("codes.safety")}</Alert>
      {dtc.source && (
        <p className="text-base text-slate-600 dark:text-slate-400">
          {t("codes.source", { source: dtc.source, license: dtc.source_license })}
        </p>
      )}
    </div>
  );
}
