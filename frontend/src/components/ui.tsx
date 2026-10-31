import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { Link, type LinkProps } from "react-router-dom";

const base =
  "inline-flex min-h-14 items-center justify-center gap-2 rounded-xl px-5 text-lg font-bold transition active:scale-[.98] disabled:opacity-50 disabled:active:scale-100";
const variants = {
  primary: "bg-amber-400 text-slate-950 hover:bg-amber-300",
  secondary:
    "border-2 border-slate-400 text-slate-900 hover:bg-slate-100 dark:border-slate-500 dark:text-slate-50 dark:hover:bg-slate-800",
  danger: "border-2 border-red-600 text-red-700 hover:bg-red-50 dark:border-red-400 dark:text-red-300 dark:hover:bg-red-950",
} as const;
type Variant = keyof typeof variants;

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />;
}

export function LinkButton({ variant = "primary", className = "", ...props }: LinkProps & { variant?: Variant }) {
  return <Link className={`${base} ${variants[variant]} ${className}`} {...props} />;
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border-2 border-slate-200 p-4 dark:border-slate-800 ${className}`}>
      {children}
    </section>
  );
}

export function PageTitle({ children }: { children: ReactNode }) {
  return <h1 className="mb-4 text-3xl font-extrabold leading-tight">{children}</h1>;
}

const fieldCls =
  "min-h-14 w-full rounded-xl border-2 border-slate-400 bg-white px-4 text-lg text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-50";

export function Label({ htmlFor, children }: { htmlFor: string; children: ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block font-semibold">
      {children}
    </label>
  );
}

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${fieldCls} ${className}`} {...props} />;
}

export function Select({ className = "", ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`${fieldCls} ${className}`} {...props} />;
}

export function Alert({ kind = "error", children }: { kind?: "error" | "warning" | "info"; children: ReactNode }) {
  const styles = {
    error: "border-red-600 bg-red-50 text-red-900 dark:bg-red-950 dark:text-red-100",
    warning: "border-amber-500 bg-amber-50 text-amber-950 dark:bg-amber-950 dark:text-amber-100",
    info: "border-sky-600 bg-sky-50 text-sky-950 dark:bg-sky-950 dark:text-sky-100",
  };
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`rounded-xl border-l-8 p-4 ${styles[kind]}`}>
      {children}
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <div role="status" className="flex items-center gap-3 py-6 text-lg">
      <span className="size-6 animate-spin rounded-full border-4 border-amber-400 border-t-transparent" />
      {label}
    </div>
  );
}
