// Editor forms for each kind of entry. `d` is the entry's data (metric units).
import { useTranslation } from "react-i18next";
import { Button, Card, Label, Select } from "../../components/ui";
import type { Kind } from "../../lib/types";
import { LinesField, PhotoField, PlainNumber, TextArea, TextField, UnitNumber } from "./fields";

/* eslint-disable @typescript-eslint/no-explicit-any */
type D = Record<string, any>;
type Props = { d: D; set: (patch: D) => void };

const THREADS = ["unspecified", "dry", "oiled", "threadlocker", "anti_seize"];
const FLUIDS = ["engine_oil", "coolant", "automatic_transmission", "manual_transmission", "cvt", "transfer_case", "front_differential", "rear_differential", "brake", "power_steering", "refrigerant", "refrigerant_oil", "fuel_tank", "washer", "other"];
const QUANTITIES = ["length", "pressure", "temperature", "mass", "volume", "voltage", "resistance", "current", "speed_rpm", "percent", "time_s", "other"];
const SOURCE_TYPES = ["owner_manual", "oem_public", "measured", "experience", "industry_standard", "other"];

export function emptyData(kind: Kind): D {
  switch (kind) {
    case "procedure":
      return { summary: "", difficulty: 3, tools: [], parts: [], warnings: [], steps: [{ text: "" }], sources: [] };
    case "torque_spec":
      return { component: "", stages: [{ type: "torque", value_nm: null }], thread_condition: "unspecified", replace_fasteners: false, sources: [{ type: "owner_manual", citation: "" }] };
    case "fluid_capacity":
      return { system: "engine_oil", amount: null, amount_unit: "L", sources: [{ type: "owner_manual", citation: "" }] };
    case "spec":
      return { name: "", quantity: "length", value: null, sources: [{ type: "owner_manual", citation: "" }] };
    case "part_note":
      return { part_name: "", oem_numbers: [], aftermarket: [], sources: [] };
    case "labor_time":
      return { job: "", includes: [], excludes: [] };
  }
}

function move<T>(arr: T[], i: number, by: number): T[] {
  const next = [...arr];
  const [x] = next.splice(i, 1);
  next.splice(i + by, 0, x);
  return next;
}

function ProcedureForm({ d, set }: Props) {
  const { t } = useTranslation();
  const steps: D[] = d.steps ?? [];
  const setStep = (i: number, patch: D) => set({ steps: steps.map((s, j) => (j === i ? { ...s, ...patch } : s)) });
  return (
    <div className="space-y-4">
      <TextArea id="f-summary" label={t("editor.summary")} value={d.summary ?? ""} onChange={(v) => set({ summary: v })} rows={3} />
      <div className="grid grid-cols-2 gap-3">
        <PlainNumber id="f-diff" label={t("editor.difficulty")} value={d.difficulty} step="1" onChange={(v) => set({ difficulty: v ?? 3 })} />
        <PlainNumber id="f-time" label={t("editor.timeMinutes")} value={d.time_minutes} step="1" onChange={(v) => set({ time_minutes: v })} />
      </div>
      <LinesField id="f-tools" label={t("editor.toolsLabel")} value={d.tools} onChange={(v) => set({ tools: v })} />
      <LinesField id="f-parts" label={t("editor.partsLabel")} value={d.parts} onChange={(v) => set({ parts: v })} />
      <LinesField id="f-warn" label={t("editor.warningsLabel")} value={d.warnings} onChange={(v) => set({ warnings: v })} />
      {steps.map((s, i) => (
        <Card key={i} className="space-y-3">
          <h3 className="text-lg font-bold">{t("editor.step", { n: i + 1 })}</h3>
          <TextArea id={`s-${i}`} label={t("editor.stepText")} value={s.text ?? ""} onChange={(v) => setStep(i, { text: v })} rows={3} />
          <TextField id={`sc-${i}`} label={t("editor.stepCaution")} value={s.caution ?? ""} max={500} onChange={(v) => setStep(i, { caution: v || null })} />
          <div className="grid grid-cols-2 gap-3">
            <UnitNumber id={`st-${i}`} quantity="torque" label={(u) => t("editor.stepTorque", { unit: u })} si={s.torque_nm} onChange={(v) => setStep(i, { torque_nm: v })} />
            <TextField id={`stl-${i}`} label={t("editor.stepTorqueLabel")} value={s.torque_label ?? ""} max={120} onChange={(v) => setStep(i, { torque_label: v || null })} />
          </div>
          <PhotoField photoId={s.photo_id} onChange={(id) => setStep(i, { photo_id: id })} />
          <div className="grid grid-cols-3 gap-2">
            <Button type="button" variant="secondary" disabled={i === 0} onClick={() => set({ steps: move(steps, i, -1) })}>↑ {t("editor.moveUp")}</Button>
            <Button type="button" variant="secondary" disabled={i === steps.length - 1} onClick={() => set({ steps: move(steps, i, 1) })}>↓ {t("editor.moveDown")}</Button>
            <Button type="button" variant="danger" disabled={steps.length === 1} onClick={() => set({ steps: steps.filter((_, j) => j !== i) })}>{t("editor.removeStep")}</Button>
          </div>
        </Card>
      ))}
      <Button type="button" variant="secondary" className="w-full" onClick={() => set({ steps: [...steps, { text: "" }] })}>+ {t("editor.addStep")}</Button>
      <TextArea id="f-notes" label={t("editor.notes")} value={d.notes ?? ""} onChange={(v) => set({ notes: v || null })} />
    </div>
  );
}

function TorqueForm({ d, set }: Props) {
  const { t } = useTranslation();
  const stages: D[] = d.stages ?? [];
  const setStage = (i: number, patch: D) => set({ stages: stages.map((s, j) => (j === i ? { ...s, ...patch } : s)) });
  return (
    <div className="space-y-4">
      <TextField id="f-comp" label={t("editor.component")} value={d.component ?? ""} required onChange={(v) => set({ component: v })} />
      <TextField id="f-fast" label={t("editor.fastener")} value={d.fastener ?? ""} onChange={(v) => set({ fastener: v || null })} />
      {stages.map((s, i) => (
        <div key={i} className="flex items-end gap-2">
          <div className="flex-1">
            {s.type === "torque" ? (
              <UnitNumber id={`stg-${i}`} quantity="torque" required label={(u) => `${t("entry.stage", { n: i + 1 })} — ${t("editor.stageValue", { unit: u })}`} si={s.value_nm} onChange={(v) => setStage(i, { value_nm: v })} />
            ) : (
              <PlainNumber id={`stg-${i}`} required label={`${t("entry.stage", { n: i + 1 })} — ${t("editor.stageAngle")}`} value={s.degrees} step="1" onChange={(v) => setStage(i, { degrees: v })} />
            )}
          </div>
          {i > 0 && <Button type="button" variant="danger" onClick={() => set({ stages: stages.filter((_, j) => j !== i) })}>✕</Button>}
        </div>
      ))}
      <div className="grid grid-cols-2 gap-3">
        <Button type="button" variant="secondary" onClick={() => set({ stages: [...stages, { type: "torque", value_nm: null }] })}>+ {t("editor.addTorqueStage")}</Button>
        <Button type="button" variant="secondary" onClick={() => set({ stages: [...stages, { type: "angle", degrees: 90 }] })}>+ {t("editor.addAngleStage")}</Button>
      </div>
      <div>
        <Label htmlFor="f-thread">{t("editor.threadCondition")}</Label>
        <Select id="f-thread" value={d.thread_condition ?? "unspecified"} onChange={(e) => set({ thread_condition: e.target.value })}>
          {THREADS.map((x) => <option key={x} value={x}>{t(`entry.threads.${x}`)}</option>)}
        </Select>
      </div>
      <label className="flex min-h-12 items-center gap-3 text-lg">
        <input type="checkbox" className="size-7 accent-amber-400" checked={!!d.replace_fasteners} onChange={(e) => set({ replace_fasteners: e.target.checked })} />
        {t("editor.replaceFasteners")}
      </label>
      <TextArea id="f-seq" label={t("editor.sequenceNote")} value={d.sequence_note ?? ""} rows={2} max={1000} onChange={(v) => set({ sequence_note: v || null })} />
      <TextArea id="f-notes" label={t("editor.notes")} value={d.notes ?? ""} rows={2} onChange={(v) => set({ notes: v || null })} />
    </div>
  );
}

function FluidForm({ d, set }: Props) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="f-sys">{t("editor.fluidSystem")}</Label>
        <Select id="f-sys" value={d.system} onChange={(e) => set({ system: e.target.value, amount_unit: e.target.value === "refrigerant" ? "g" : d.amount_unit })}>
          {FLUIDS.map((x) => <option key={x} value={x}>{t(`entry.fluidSystems.${x}`)}</option>)}
        </Select>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <PlainNumber id="f-amt" label={t("editor.amount")} value={d.amount} onChange={(v) => set({ amount: v })} />
        <PlainNumber id="f-amt-max" label={t("editor.amountMax")} value={d.amount_max} onChange={(v) => set({ amount_max: v })} />
        <div>
          <Label htmlFor="f-unit">{t("editor.amountUnit")}</Label>
          <Select id="f-unit" value={d.amount_unit} onChange={(e) => set({ amount_unit: e.target.value })}>
            {["L", "mL", "kg", "g"].map((u) => <option key={u} value={u}>{u}</option>)}
          </Select>
        </div>
      </div>
      <TextField id="f-cond" label={t("editor.condition")} value={d.condition ?? ""} onChange={(v) => set({ condition: v || null })} />
      <TextField id="f-spec" label={t("editor.fluidSpec")} value={d.fluid_spec ?? ""} onChange={(v) => set({ fluid_spec: v || null })} />
      <TextArea id="f-notes" label={t("editor.notes")} value={d.notes ?? ""} rows={2} onChange={(v) => set({ notes: v || null })} />
    </div>
  );
}

function SpecForm({ d, set }: Props) {
  const { t } = useTranslation();
  const convertible = ["length", "pressure", "temperature", "mass", "volume"].includes(d.quantity);
  return (
    <div className="space-y-4">
      <TextField id="f-name" label={t("editor.specName")} value={d.name ?? ""} required onChange={(v) => set({ name: v })} />
      <div>
        <Label htmlFor="f-q">{t("editor.quantity")}</Label>
        <Select id="f-q" value={d.quantity} onChange={(e) => set({ quantity: e.target.value, value: null, value_max: null })}>
          {QUANTITIES.map((x) => <option key={x} value={x}>{t(`editor.quantities.${x}`)}</option>)}
        </Select>
      </div>
      {convertible ? (
        <div className="grid grid-cols-2 gap-3" key={d.quantity}>
          <UnitNumber id="f-val" required quantity={d.quantity} label={(u) => t("editor.value", { unit: u })} si={d.value} onChange={(v) => set({ value: v })} />
          <UnitNumber id="f-max" quantity={d.quantity} label={() => t("editor.valueMax")} si={d.value_max} onChange={(v) => set({ value_max: v })} />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3" key={d.quantity}>
          <PlainNumber id="f-val" required label={t("editor.value", { unit: "" })} value={d.value} onChange={(v) => set({ value: v })} />
          <PlainNumber id="f-max" label={t("editor.valueMax")} value={d.value_max} onChange={(v) => set({ value_max: v })} />
        </div>
      )}
      {d.quantity === "other" && <TextField id="f-uo" label={t("editor.unitOther")} value={d.unit_other ?? ""} max={20} onChange={(v) => set({ unit_other: v || null })} />}
      <TextField id="f-cond" label={t("editor.condition")} value={d.condition ?? ""} onChange={(v) => set({ condition: v || null })} />
      <TextArea id="f-notes" label={t("editor.notes")} value={d.notes ?? ""} rows={2} onChange={(v) => set({ notes: v || null })} />
    </div>
  );
}

function PartForm({ d, set }: Props) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <TextField id="f-part" label={t("editor.partName")} value={d.part_name ?? ""} required onChange={(v) => set({ part_name: v })} />
      <LinesField id="f-oem" label={t("editor.oemNumbers")} value={d.oem_numbers} onChange={(v) => set({ oem_numbers: v })} />
      <LinesField id="f-aft" label={t("editor.aftermarket")} value={d.aftermarket} onChange={(v) => set({ aftermarket: v })} />
      <TextArea id="f-fit" label={t("editor.fitment")} value={d.fitment_notes ?? ""} rows={3} onChange={(v) => set({ fitment_notes: v || null })} />
      <TextArea id="f-notes" label={t("editor.notes")} value={d.notes ?? ""} rows={2} onChange={(v) => set({ notes: v || null })} />
    </div>
  );
}

function LaborForm({ d, set }: Props) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <TextField id="f-job" label={t("editor.job")} value={d.job ?? ""} required onChange={(v) => set({ job: v })} />
      <LinesField id="f-inc" label={t("editor.includes")} value={d.includes} onChange={(v) => set({ includes: v })} />
      <LinesField id="f-exc" label={t("editor.excludes")} value={d.excludes} onChange={(v) => set({ excludes: v })} />
      <TextArea id="f-notes" label={t("editor.notes")} value={d.notes ?? ""} rows={2} onChange={(v) => set({ notes: v || null })} />
    </div>
  );
}

export function SourcesForm({ d, set }: Props) {
  const { t } = useTranslation();
  const sources: D[] = d.sources ?? [];
  const setSrc = (i: number, patch: D) => set({ sources: sources.map((s, j) => (j === i ? { ...s, ...patch } : s)) });
  return (
    <Card className="space-y-3">
      <h2 className="text-xl font-bold">{t("editor.sourcesTitle")}</h2>
      <p className="text-base text-slate-600 dark:text-slate-400">{t("editor.sourcesHelp")}</p>
      {sources.map((s, i) => (
        <div key={i} className="space-y-2 rounded-xl border-2 border-slate-200 p-3 dark:border-slate-800">
          <Label htmlFor={`src-${i}`}>{t("editor.sourceType")}</Label>
          <Select id={`src-${i}`} value={s.type} onChange={(e) => setSrc(i, { type: e.target.value })}>
            {SOURCE_TYPES.map((x) => <option key={x} value={x}>{t(`entry.sourceTypes.${x}`)}</option>)}
          </Select>
          <TextField id={`cit-${i}`} label={t("editor.citation")} value={s.citation ?? ""} max={300} onChange={(v) => setSrc(i, { citation: v })} />
          <Button type="button" variant="danger" onClick={() => set({ sources: sources.filter((_, j) => j !== i) })}>{t("editor.removeSource")}</Button>
        </div>
      ))}
      <Button type="button" variant="secondary" className="w-full" onClick={() => set({ sources: [...sources, { type: "experience", citation: "" }] })}>+ {t("editor.addSource")}</Button>
    </Card>
  );
}

export function KindForm({ kind, d, set }: Props & { kind: Kind }) {
  switch (kind) {
    case "procedure": return <ProcedureForm d={d} set={set} />;
    case "torque_spec": return <TorqueForm d={d} set={set} />;
    case "fluid_capacity": return <FluidForm d={d} set={set} />;
    case "spec": return <SpecForm d={d} set={set} />;
    case "part_note": return <PartForm d={d} set={set} />;
    case "labor_time": return <LaborForm d={d} set={set} />;
  }
}
