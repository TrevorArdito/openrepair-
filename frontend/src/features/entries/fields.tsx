// Small form building blocks for the guide/spec editor.
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, Input, Label } from "../../components/ui";
import { apiUpload } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { usePrefs } from "../../lib/prefs";
import { convert, toSI, type Quantity } from "../../lib/units";

const area =
  "min-h-28 w-full rounded-xl border-2 border-slate-400 bg-white p-3 text-lg text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-50";

export function TextArea({ id, label, value, onChange, rows = 4, max = 4000, hint }: { id: string; label: string; value: string; onChange: (v: string) => void; rows?: number; max?: number; hint?: string }) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <textarea id={id} rows={rows} maxLength={max} value={value} onChange={(e) => onChange(e.target.value)} className={area} />
      {hint && <p className="mt-1 text-base text-slate-600 dark:text-slate-400">{hint}</p>}
    </div>
  );
}

export function TextField({ id, label, value, onChange, max = 200, hint, required }: { id: string; label: string; value: string; onChange: (v: string) => void; max?: number; hint?: string; required?: boolean }) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} value={value} maxLength={max} required={required} onChange={(e) => onChange(e.target.value)} />
      {hint && <p className="mt-1 text-base text-slate-600 dark:text-slate-400">{hint}</p>}
    </div>
  );
}

/** "One per line" text area <-> string[] */
export function LinesField({ id, label, value, onChange }: { id: string; label: string; value: string[] | undefined; onChange: (v: string[]) => void }) {
  const [text, setText] = useState((value ?? []).join("\n"));
  return (
    <TextArea
      id={id}
      label={label}
      rows={3}
      value={text}
      onChange={(t) => {
        setText(t);
        onChange(t.split("\n").map((s) => s.trim()).filter(Boolean));
      }}
    />
  );
}

/** Number typed in the user's units, stored in metric (SI). */
export function UnitNumber({ id, label, si, quantity, onChange, required }: { id: string; label: (unit: string) => string; si: number | undefined | null; quantity: Quantity; onChange: (si: number | null) => void; required?: boolean }) {
  const { units } = usePrefs();
  const unit = convert(1, quantity, units).unit;
  const [text, setText] = useState(si == null ? "" : String(Number(convert(si, quantity, units).value.toFixed(2))));
  return (
    <div>
      <Label htmlFor={id}>{label(unit)}</Label>
      <Input
        id={id}
        type="number"
        inputMode="decimal"
        step="any"
        required={required}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          const n = parseFloat(e.target.value);
          onChange(Number.isFinite(n) ? Number(toSI(n, quantity, units).toFixed(3)) : null);
        }}
      />
    </div>
  );
}

export function PlainNumber({ id, label, value, onChange, step = "any", required }: { id: string; label: string; value: number | undefined | null; onChange: (v: number | null) => void; step?: string; required?: boolean }) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} type="number" inputMode="decimal" step={step} required={required} value={value ?? ""}
        onChange={(e) => { const n = parseFloat(e.target.value); onChange(Number.isFinite(n) ? n : null); }} />
    </div>
  );
}

export function PhotoField({ photoId, onChange }: { photoId?: number | null; onChange: (id: number | null) => void }) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (photoId)
    return (
      <div className="space-y-2">
        <img src={`/api/v1/photos/${photoId}`} alt="" className="max-h-60 rounded-xl" />
        <Button type="button" variant="secondary" onClick={() => onChange(null)}>{t("editor.removePhoto")}</Button>
      </div>
    );
  return (
    <div>
      <label className="flex min-h-14 cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-slate-400 px-4 text-lg font-semibold">
        📷 {busy ? t("editor.uploading") : t("editor.stepPhoto")}
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          className="sr-only"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            setBusy(true);
            setError(null);
            try {
              onChange((await apiUpload<{ id: number }>("/photos", file)).id);
            } catch (err) {
              setError(errorMessage(t, err));
            } finally {
              setBusy(false);
            }
          }}
        />
      </label>
      {error && <p className="mt-1 font-semibold text-red-700 dark:text-red-400">{error}</p>}
    </div>
  );
}
