// How each kind of entry is displayed. Numbers are stored metric and shown in the
// reader's chosen units.
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Alert, Button, Card, Input, Label, Select } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { usePrefs } from "../../lib/prefs";
import type { Entry } from "../../lib/types";
import { formatQuantity, type Quantity } from "../../lib/units";
import { fluidAmount, specValue } from "./specFormat";

/* eslint-disable @typescript-eslint/no-explicit-any */
type D = Record<string, any>;

export function useTorque() {
  const { units } = usePrefs();
  return (nm: number) => formatQuantity(nm, "torque", units, 0);
}

function useVolume() {
  const { units } = usePrefs();
  return (l: number) => formatQuantity(l, "volume", units, 1);
}

function Lines({ title, items, ordered = false }: { title: string; items?: string[]; ordered?: boolean }) {
  if (!items?.length) return null;
  const Tag = ordered ? "ol" : "ul";
  return (
    <Card>
      <h2 className="mb-2 text-xl font-bold">{title}</h2>
      <Tag className={`${ordered ? "list-decimal" : "list-disc"} space-y-1 pl-6 text-lg`}>
        {items.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </Tag>
    </Card>
  );
}

function BigValue({ value, sub }: { value: string; sub?: string }) {
  return (
    <div className="rounded-2xl bg-slate-900 p-5 text-center text-white dark:bg-slate-800">
      <p className="font-mono text-5xl font-extrabold tracking-tight text-amber-400">{value}</p>
      {sub && <p className="mt-2 text-lg">{sub}</p>}
    </div>
  );
}

// Unit-aware display of a guide's spec value (stored SI; shown in the user's units).
const UNIT_QUANTITY: Record<string, Quantity> = { mm: "length", kPa: "pressure", "°C": "temperature", Nm: "torque", L: "volume", kg: "mass" };

function useSpecText() {
  const { units } = usePrefs();
  return (sp: D): string => {
    if (sp.value == null) return sp.text ?? "";
    const q = sp.unit ? UNIT_QUANTITY[sp.unit] : undefined;
    // Small lengths (plug gaps, clearances) need 3 decimals in inches: 1.0 mm = 0.039 in.
    const digits = (v: number) => (q === "length" && v < 5 ? 3 : 2);
    const fmt = (v: number) => (q ? formatQuantity(v, q, units, digits(v), true) : `${v}${sp.unit ? ` ${sp.unit}` : ""}`);
    const main = sp.value_max != null ? `${fmt(sp.value)} – ${fmt(sp.value_max)}` : fmt(sp.value);
    return sp.text ? `${main} (${sp.text})` : main;
  };
}

function Unverified() {
  const { t } = useTranslation();
  return <span className="ml-1 rounded bg-red-700 px-2 py-0.5 text-sm font-bold uppercase text-white" title={t("entry.unverifiedHint")}>{t("entry.unverifiedTag")}</span>;
}

/** Superscript links to the page's numbered source list. */
function Refs({ refs }: { refs?: number[] }) {
  if (!refs?.length) return null;
  return <sup className="ml-1 font-semibold">{refs.map((r) => <a key={r} href={`#src-${r + 1}`} className="underline">[{r + 1}]</a>)}</sup>;
}

function SpecList({ specs }: { specs: D[] }) {
  const spec = useSpecText();
  return (
    <ul className="mt-2 space-y-1">
      {specs.map((sp: D, i: number) => (
        <li key={i} className="rounded-lg bg-slate-900 px-3 py-2 font-mono text-lg font-bold text-amber-400">
          {sp.name}: {spec(sp)}
          {sp.unverified && <Unverified />}
          <Refs refs={sp.source_refs} />
        </li>
      ))}
    </ul>
  );
}

function DtcGuideView({ d }: { d: D }) {
  const { t } = useTranslation();
  const money = (n: number) => new Intl.NumberFormat(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
  const causes = [...(d.causes ?? [])].sort((a: D, b: D) => a.rank - b.rank);
  return (
    <div className="space-y-4">
      {d.warnings?.length > 0 && (
        <Alert kind="warning">
          <h2 className="mb-1 font-bold">{t("entry.warnings")}</h2>
          <ul className="list-disc pl-5">{d.warnings.map((w: string) => <li key={w}>{w}</li>)}</ul>
        </Alert>
      )}
      <Card className="space-y-2">
        <p className="font-mono text-2xl font-extrabold">{d.code}</p>
        <p className="text-lg">{d.definition}</p>
        <p className="text-lg"><b>{t("entry.applications")}:</b> {d.applications}</p>
      </Card>
      <Card className="space-y-2">
        <h2 className="text-xl font-bold">{t("dtcGuide.monitor")}</h2>
        <p className="whitespace-pre-line text-lg">{d.monitor}</p>
        {d.enable_criteria?.length > 0 && (
          <>
            <h3 className="pt-2 text-lg font-bold">{t("dtcGuide.enableCriteria")}</h3>
            <ul className="list-disc pl-5 text-lg">{d.enable_criteria.map((c: string) => <li key={c}>{c}</li>)}</ul>
          </>
        )}
      </Card>
      <Lines title={t("dtcGuide.symptoms")} items={d.symptoms} />
      <Card>
        <h2 className="mb-2 text-xl font-bold">{t("dtcGuide.causes")}</h2>
        <ol className="space-y-2 text-lg">
          {causes.map((c: D) => (
            <li key={c.rank + c.cause} className="flex gap-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-full border-2 border-slate-400 font-bold">{c.rank}</span>
              <span>
                <b>{c.cause}</b>
                {c.pattern_failure && <span className="ml-2 rounded bg-amber-500 px-2 py-0.5 text-sm font-bold uppercase text-slate-950">{t("dtcGuide.pattern")}</span>}
                <Refs refs={c.source_refs} />
                {c.note && <span className="block text-base">{c.note}</span>}
              </span>
            </li>
          ))}
        </ol>
      </Card>
      <Card>
        <h2 className="mb-3 text-xl font-bold">{t("dtcGuide.tests")}</h2>
        <ol className="space-y-3">
          {d.tests.map((ts: D, i: number) => (
            <li key={i} id={`test-${i + 1}`} className="rounded-xl border-2 border-slate-300 p-3 dark:border-slate-700">
              <h3 className="text-lg font-bold">{t("dtcGuide.testN", { n: i + 1 })}: {ts.title} <Refs refs={ts.source_refs} /></h3>
              {ts.caution && <p className="mt-2 rounded-lg bg-amber-100 p-2 font-semibold text-amber-950 dark:bg-amber-950 dark:text-amber-100">⚠ {ts.caution}</p>}
              <p className="mt-2 whitespace-pre-line text-lg">{ts.how}</p>
              {ts.connector_pin && <p className="mt-2 text-lg"><b>{t("dtcGuide.pins")}:</b> {ts.connector_pin}</p>}
              {ts.specs?.length > 0 && <SpecList specs={ts.specs} />}
              {(ts.good || ts.bad) && (
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  {ts.good && <p className="rounded-lg border-2 border-green-600 p-2 text-lg"><b>✓ {t("dtcGuide.good")}:</b> {ts.good}</p>}
                  {ts.bad && <p className="rounded-lg border-2 border-red-600 p-2 text-lg"><b>✗ {t("dtcGuide.bad")}:</b> {ts.bad}</p>}
                </div>
              )}
            </li>
          ))}
        </ol>
      </Card>
      {d.related?.length > 0 && (
        <Card>
          <h2 className="mb-2 text-xl font-bold">{t("dtcGuide.related")}</h2>
          <ul className="space-y-1 text-lg">
            {d.related.map((b: D) => (
              <li key={b.number}><b>{t(`dtcGuide.bulletin.${b.type}`)} {b.number}</b>{b.summary ? ` — ${b.summary}` : ""} <Refs refs={b.source_refs} /></li>
            ))}
          </ul>
        </Card>
      )}
      <Lines title={t("dtcGuide.misdiagnoses")} items={d.misdiagnoses} />
      {(d.repair_hours || d.parts_cost_usd) && (
        <Card className="space-y-1 text-lg">
          <h2 className="mb-1 text-xl font-bold">{t("dtcGuide.costTime")}</h2>
          {d.repair_hours && <p>{t("dtcGuide.hours", { min: d.repair_hours.min, max: d.repair_hours.max })}{d.repair_hours.note ? ` — ${d.repair_hours.note}` : ""}</p>}
          {d.parts_cost_usd && <p>{t("dtcGuide.parts", { min: money(d.parts_cost_usd.min), max: money(d.parts_cost_usd.max) })}{d.parts_cost_usd.note ? ` — ${d.parts_cost_usd.note}` : ""}</p>}
        </Card>
      )}
      {d.notes && <Card><p className="whitespace-pre-line text-lg">{d.notes}</p></Card>}
    </div>
  );
}

function ProcedureView({ d }: { d: D }) {
  const { t } = useTranslation();
  const torque = useTorque();
  const volume = useVolume();
  const [done, setDone] = useState<number[]>([]);
  return (
    <div className="space-y-4">
      <p className="text-lg">{d.summary}</p>
      <div className="flex flex-wrap gap-3 text-lg">
        <span className="rounded-lg border-2 border-slate-300 px-3 py-1 dark:border-slate-700">
          {t("entry.difficulty")}: <b>{t(`entry.difficultyLevels.${d.difficulty ?? 3}`)}</b>
        </span>
        {d.time_minutes && (
          <span className="rounded-lg border-2 border-slate-300 px-3 py-1 dark:border-slate-700">
            {t("entry.time")}: <b>{t("entry.minutes", { count: d.time_minutes })}</b>
          </span>
        )}
      </div>
      {d.warnings?.length > 0 && (
        <Alert kind="warning">
          <h2 className="mb-1 font-bold">{t("entry.warnings")}</h2>
          <ul className="list-disc pl-5">
            {d.warnings.map((w: string) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Alert>
      )}
      {d.applications && <p className="text-lg"><b>{t("entry.applications")}:</b> {d.applications}</p>}
      <Lines title={t("entry.tools")} items={d.tools} />
      <Lines title={t("entry.specialTools")} items={d.special_tools} />
      <Lines title={t("entry.parts")} items={d.parts} />
      {d.fluids?.length > 0 && (
        <Card>
          <h2 className="mb-2 text-xl font-bold">{t("entry.fluids")}</h2>
          <ul className="space-y-2 text-lg">
            {d.fluids.map((f: D, i: number) => (
              <li key={i}>
                <b>{f.name}</b>{f.capacity_l ? ` — ${volume(f.capacity_l)}` : ""}{f.printed ? ` (${f.printed})` : ""}
                {f.spec && <span className="block text-base">{f.spec}</span>}
                {f.unverified && <Unverified />} <Refs refs={f.source_refs} />
              </li>
            ))}
          </ul>
        </Card>
      )}
      <Card>
        <h2 className="mb-3 text-xl font-bold">{t("entry.steps")}</h2>
        <ol className="space-y-3">
          {d.steps.map((s: D, i: number) => {
            const checked = done.includes(i);
            return (
              <li key={i} className={`rounded-xl border-2 p-3 ${checked ? "border-green-600 bg-green-50 dark:bg-green-950" : "border-slate-300 dark:border-slate-700"}`}>
                <button
                  type="button"
                  role="checkbox"
                  aria-checked={checked}
                  onClick={() => setDone(checked ? done.filter((x) => x !== i) : [...done, i])}
                  className="flex w-full items-start gap-3 text-left text-lg"
                >
                  <span className={`flex size-9 shrink-0 items-center justify-center rounded-full border-2 font-bold ${checked ? "border-green-600 bg-green-600 text-white" : "border-slate-400"}`} aria-hidden="true">
                    {checked ? "✓" : i + 1}
                  </span>
                  <span className={checked ? "opacity-70" : ""}>{s.text}</span>
                </button>
                {s.caution && (
                  <p className="mt-2 rounded-lg bg-amber-100 p-2 font-semibold text-amber-950 dark:bg-amber-950 dark:text-amber-100">
                    ⚠ {t("entry.stepCaution")}: {s.caution}
                  </p>
                )}
                {s.torque_nm && (
                  <p className="mt-2 inline-block rounded-lg bg-slate-900 px-3 py-2 font-mono text-xl font-bold text-amber-400">
                    {s.torque_label ? `${s.torque_label}: ` : ""}
                    {torque(s.torque_nm)}
                  </p>
                )}
                {s.sequence && <p className="mt-2 text-lg"><b>{t("entry.sequence")}:</b> {s.sequence}</p>}
                {s.specs?.length > 0 && <SpecList specs={s.specs} />}
                <Refs refs={s.source_refs} />
                {s.photo_id && <img src={`/api/v1/photos/${s.photo_id}`} alt="" loading="lazy" className="mt-2 w-full rounded-xl" />}
              </li>
            );
          })}
        </ol>
      </Card>
      <Lines title={t("entry.gotchas")} items={d.gotchas} />
      {d.notes && (
        <Card>
          <h2 className="mb-1 text-xl font-bold">{t("entry.notes")}</h2>
          <p className="whitespace-pre-line text-lg">{d.notes}</p>
        </Card>
      )}
    </div>
  );
}

function TorqueView({ d }: { d: D }) {
  const { t } = useTranslation();
  const torque = useTorque();
  const { units } = usePrefs();
  const other = units === "metric" ? "imperial" : "metric";
  const first = d.stages[0];
  return (
    <div className="space-y-4">
      <BigValue value={torque(first.value_nm)} sub={`${formatQuantity(first.value_nm, "torque", other, 0)} · ${d.component}`} />
      {d.stages.length > 1 && (
        <Card>
          <ol className="space-y-2 text-lg">
            {d.stages.map((s: D, i: number) => (
              <li key={i} className="flex gap-3">
                <b className="w-20 shrink-0">{t("entry.stage", { n: i + 1 })}</b>
                <span className="font-mono font-bold">{s.type === "torque" ? torque(s.value_nm) : t("entry.thenAngle", { deg: s.degrees })}</span>
              </li>
            ))}
          </ol>
        </Card>
      )}
      {d.replace_fasteners && <Alert>{t("entry.replaceFasteners")}</Alert>}
      <Card>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-lg">
          {d.fastener && (
            <>
              <dt className="font-semibold">{t("entry.fastener")}</dt>
              <dd>{d.fastener}</dd>
            </>
          )}
          <dt className="font-semibold">{t("entry.threadCondition")}</dt>
          <dd>{t(`entry.threads.${d.thread_condition ?? "unspecified"}`)}</dd>
          {d.sequence_note && (
            <>
              <dt className="font-semibold">{t("entry.sequence")}</dt>
              <dd className="whitespace-pre-line">{d.sequence_note}</dd>
            </>
          )}
        </dl>
      </Card>
      {d.notes && <p className="whitespace-pre-line text-lg">{d.notes}</p>}
    </div>
  );
}

function FluidView({ d }: { d: D }) {
  const { t } = useTranslation();
  const { units } = usePrefs();
  const other = units === "metric" ? "imperial" : "metric";
  const amt = fluidAmount(d, units);
  return (
    <div className="space-y-4">
      {amt ? (
        <BigValue value={amt} sub={`${fluidAmount(d, other)} · ${t(`entry.fluidSystems.${d.system}`)}`} />
      ) : (
        <div className="rounded-2xl bg-slate-900 p-5 text-center text-white dark:bg-slate-800">
          <p className="text-2xl font-extrabold text-amber-400">{d.fluid_spec}</p>
          <p className="mt-2 text-lg">{t(`entry.fluidSystems.${d.system}`)}</p>
        </div>
      )}
      <Card>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-lg">
          {d.fluid_spec && amt && (
            <>
              <dt className="font-semibold">{t("entry.fluidSpec")}</dt>
              <dd>{d.fluid_spec}</dd>
            </>
          )}
          {d.condition && (
            <>
              <dt className="font-semibold">{t("entry.condition")}</dt>
              <dd>{d.condition}</dd>
            </>
          )}
          {d.printed && (
            <>
              <dt className="font-semibold">{t("entry.printed")}</dt>
              <dd className="font-mono">{d.printed}</dd>
            </>
          )}
        </dl>
      </Card>
      {d.notes && <p className="whitespace-pre-line text-lg">{d.notes}</p>}
    </div>
  );
}

function SpecView({ d }: { d: D }) {
  const { t } = useTranslation();
  const { units } = usePrefs();
  return (
    <div className="space-y-4">
      <BigValue value={specValue(d, units)} sub={d.name} />
      {d.printed && (
        <p className="text-lg">
          <b>{t("entry.printed")}:</b> <span className="font-mono">{d.printed}</span>
        </p>
      )}
      {d.condition && (
        <p className="text-lg">
          <b>{t("entry.condition")}:</b> {d.condition}
        </p>
      )}
      {d.notes && <p className="whitespace-pre-line text-lg">{d.notes}</p>}
    </div>
  );
}

function PartView({ d }: { d: D }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">{d.part_name}</h2>
      <Lines title={t("entry.oemNumbers")} items={d.oem_numbers} />
      <Lines title={t("entry.aftermarket")} items={d.aftermarket} />
      {d.fitment_notes && (
        <Card>
          <h2 className="mb-1 text-xl font-bold">{t("entry.fitment")}</h2>
          <p className="whitespace-pre-line text-lg">{d.fitment_notes}</p>
        </Card>
      )}
      {d.notes && <p className="whitespace-pre-line text-lg">{d.notes}</p>}
    </div>
  );
}

const BASES = ["warranty", "flat_rate", "pro_actual", "diy_actual"] as const;
const RUST = ["none", "light", "heavy"] as const;

function LaborView({ entry, d, onChange, canAdd }: { entry: Entry; d: D; onChange: (e: Entry) => void; canAdd: boolean }) {
  const { t } = useTranslation();
  const [basis, setBasis] = useState<string>("pro_actual");
  const [hours, setHours] = useState("");
  const [rust, setRust] = useState<string>("none");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState<{ kind: "error" | "info"; text: string } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      onChange(await api<Entry>(`/entries/${entry.id}/labor`, { method: "POST", body: { basis, hours: Number(hours), rust, note: note || null } }));
      setHours("");
      setNote("");
      setMsg({ kind: "info", text: t("entry.laborThanks") });
    } catch (err) {
      setMsg({ kind: "error", text: errorMessage(t, err) });
    }
  }

  const labor = entry.labor ?? {};
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">{d.job}</h2>
      <p className="text-lg">{t("entry.laborIntro")}</p>
      <div className="space-y-3">
        {BASES.map((b) => (
          <section key={b} className="rounded-2xl border-2 border-slate-200 p-3 dark:border-slate-800">
            <h3 className="mb-2 text-lg font-bold">{t(`entry.laborBasis.${b}`)}</h3>
            <div className="grid grid-cols-3 gap-2">
              {RUST.map((r) => {
                const c = labor[b]?.[r];
                const has = c && c.reports > 0;
                return (
                  <div key={r} className={`rounded-xl p-2 text-center ${has ? "bg-slate-100 dark:bg-slate-800" : "border-2 border-dashed border-slate-300 dark:border-slate-700"}`}>
                    <p className="text-sm font-semibold">{t(`entry.rust.${r}`)}</p>
                    {has ? (
                      <>
                        <p className="font-mono text-2xl font-extrabold">{t("entry.hoursValue", { h: c.median })}</p>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                          {c.min !== c.max ? `${c.min}–${c.max} h · ` : ""}
                          {t("entry.reportsCount", { count: c.reports })}
                        </p>
                      </>
                    ) : (
                      <p className="py-2 text-xl text-slate-400">{t("entry.noReports")}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>
      <Lines title={t("entry.includes")} items={d.includes} />
      <Lines title={t("entry.excludes")} items={d.excludes} />
      {d.notes && <p className="whitespace-pre-line text-lg">{d.notes}</p>}
      {canAdd && (
        <Card>
          <h2 className="mb-3 text-xl font-bold">{t("entry.addLabor")}</h2>
          <form onSubmit={submit} className="space-y-3">
            <div>
              <Label htmlFor="lb-basis">{t("entry.laborBasisLabel")}</Label>
              <Select id="lb-basis" value={basis} onChange={(e) => setBasis(e.target.value)}>
                {BASES.map((b) => (
                  <option key={b} value={b}>
                    {t(`entry.laborBasis.${b}`)}
                  </option>
                ))}
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="lb-hours">{t("entry.laborHours")}</Label>
                <Input id="lb-hours" type="number" inputMode="decimal" step="0.1" min="0.1" max="200" required value={hours} onChange={(e) => setHours(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="lb-rust">{t("entry.laborRust")}</Label>
                <Select id="lb-rust" value={rust} onChange={(e) => setRust(e.target.value)}>
                  {RUST.map((r) => (
                    <option key={r} value={r}>
                      {t(`entry.rust.${r}`)}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="lb-note">{t("entry.laborNote")}</Label>
              <Input id="lb-note" maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} />
            </div>
            {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
            <Button type="submit" className="w-full">
              {t("entry.laborSave")}
            </Button>
          </form>
        </Card>
      )}
    </div>
  );
}

export function EntryBody({ entry, onChange, loggedIn }: { entry: Entry; onChange: (e: Entry) => void; loggedIn: boolean }) {
  const d = entry.revision?.data ?? {};
  switch (entry.kind) {
    case "procedure":
      return <ProcedureView d={d} />;
    case "torque_spec":
      return <TorqueView d={d} />;
    case "fluid_capacity":
      return <FluidView d={d} />;
    case "spec":
      return <SpecView d={d} />;
    case "part_note":
      return <PartView d={d} />;
    case "labor_time":
      return <LaborView entry={entry} d={d} onChange={onChange} canAdd={loggedIn} />;
    case "dtc_guide":
      return <DtcGuideView d={d} />;
  }
}
