import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, Card, Input, Label, Select } from "../../components/ui";
import { api } from "../../lib/api";
import type { AppliesTo, EntryTags, NamedRef } from "../../lib/types";
import { PlainNumber } from "./fields";

type SystemRow = { slug: string; parent: string | null; safety_critical: boolean };

export function RangeRow({ r, makes, onChange, onRemove, idx }: { r: AppliesTo; makes: NamedRef[]; onChange: (r: AppliesTo) => void; onRemove: () => void; idx: number }) {
  const { t } = useTranslation();
  const [models, setModels] = useState<NamedRef[]>([]);
  useEffect(() => {
    if (!r.make_id || !r.year_from) return;
    api<NamedRef[]>(`/vehicles/models?year=${r.year_from}&make_id=${r.make_id}`).then(setModels).catch(() => setModels([]));
  }, [r.make_id, r.year_from]);
  return (
    <div className="space-y-2 rounded-xl border-2 border-slate-200 p-3 dark:border-slate-800">
      <div className="grid grid-cols-2 gap-3">
        <PlainNumber id={`yf-${idx}`} required label={t("editor.yearFrom")} step="1" value={r.year_from} onChange={(v) => onChange({ ...r, year_from: v ?? r.year_from })} />
        <PlainNumber id={`yt-${idx}`} required label={t("editor.yearTo")} step="1" value={r.year_to} onChange={(v) => onChange({ ...r, year_to: v ?? r.year_to })} />
      </div>
      <Label htmlFor={`mk-${idx}`}>{t("editor.make")}</Label>
      <Select id={`mk-${idx}`} value={r.make_id} onChange={(e) => onChange({ ...r, make_id: Number(e.target.value), model_id: null })}>
        {makes.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
      </Select>
      <Label htmlFor={`md-${idx}`}>{t("editor.model")}</Label>
      <Select id={`md-${idx}`} value={r.model_id ?? ""} onChange={(e) => onChange({ ...r, model_id: e.target.value ? Number(e.target.value) : null })}>
        <option value="">{t("editor.anyModel")}</option>
        {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
      </Select>
      <PlainNumber id={`dl-${idx}`} label={t("editor.displacement")} value={r.displacement_l} onChange={(v) => onChange({ ...r, displacement_l: v })} />
      <Button type="button" variant="danger" onClick={onRemove}>{t("editor.removeRange")}</Button>
    </div>
  );
}

export default function TagsForm({ tags, set }: { tags: EntryTags; set: (t: EntryTags) => void }) {
  const { t } = useTranslation();
  const [makes, setMakes] = useState<NamedRef[]>([]);
  const [systems, setSystems] = useState<SystemRow[]>([]);
  const [dtcText, setDtcText] = useState(tags.dtcs.join(", "));
  useEffect(() => {
    api<NamedRef[]>("/vehicles/makes").then(setMakes).catch(() => undefined);
    api<SystemRow[]>("/systems").then(setSystems).catch(() => undefined);
  }, []);
  const year = new Date().getFullYear();

  return (
    <Card className="space-y-4">
      <h2 className="text-xl font-bold">{t("editor.tagsTitle")}</h2>
      {tags.applies_to.length === 0 && <p className="text-lg font-semibold">{t("editor.generic")}</p>}
      {tags.applies_to.map((r, i) => (
        <RangeRow key={i} idx={i} r={r} makes={makes}
          onChange={(nr) => set({ ...tags, applies_to: tags.applies_to.map((x, j) => (j === i ? nr : x)) })}
          onRemove={() => set({ ...tags, applies_to: tags.applies_to.filter((_, j) => j !== i) })} />
      ))}
      <Button type="button" variant="secondary" className="w-full" disabled={!makes.length}
        onClick={() => set({ ...tags, applies_to: [...tags.applies_to, { make_id: makes[0].id, model_id: null, year_from: year - 5, year_to: year }] })}>
        + {t("editor.addVehicleRange")}
      </Button>

      <fieldset>
        <legend className="mb-2 text-lg font-bold">{t("editor.systemsTitle")}</legend>
        <div className="flex flex-wrap gap-2">
          {systems.map((s) => {
            const on = tags.systems.includes(s.slug);
            return (
              <button key={s.slug} type="button" aria-pressed={on}
                onClick={() => set({ ...tags, systems: on ? tags.systems.filter((x) => x !== s.slug) : [...tags.systems, s.slug].slice(0, 10) })}
                className={`min-h-12 rounded-full border-2 px-3 text-base font-semibold ${on ? "border-amber-400 bg-amber-400 text-slate-950" : "border-slate-300 dark:border-slate-600"} ${s.parent ? "" : "font-extrabold"}`}>
                {t(`systems.${s.slug}`)}
              </button>
            );
          })}
        </div>
      </fieldset>

      <div>
        <Label htmlFor="f-dtcs">{t("editor.dtcsLabel")}</Label>
        <Input id="f-dtcs" value={dtcText} className="font-mono uppercase" placeholder="P0420, P0430"
          onChange={(e) => {
            setDtcText(e.target.value);
            set({ ...tags, dtcs: e.target.value.split(/[,\s]+/).map((s) => s.trim().toUpperCase()).filter(Boolean) });
          }} />
      </div>
    </Card>
  );
}
