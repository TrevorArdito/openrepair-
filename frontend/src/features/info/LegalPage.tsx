import { Fragment, useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { Alert, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { useDocumentTitle } from "../../lib/title";

type Doc = { name: string; version: string | null; draft: boolean; markdown: string };

// Tiny Markdown renderer for our own legal documents: headings, lists, quotes, bold, links.
function inline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)]+)\)|\*(.+?)\*/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    out.push(text.slice(last, m.index));
    if (m[1]) out.push(<strong key={m.index}>{m[1]}</strong>);
    else if (m[2]) {
      const slug = m[3].replace(/\.md$/, "").toLowerCase().replace(/_/g, "-").replace("terms-of-service", "terms");
      out.push(m[3].endsWith(".md") ? <Link key={m.index} className="underline" to={`/legal/${slug}`}>{m[2]}</Link> : m[2]);
    } else if (m[4]) out.push(<em key={m.index}>{m[4]}</em>);
    last = re.lastIndex;
  }
  out.push(text.slice(last));
  return out;
}

function render(md: string): ReactNode[] {
  const blocks: ReactNode[] = [];
  let list: string[] = [];
  let para: string[] = [];
  let quote = false;
  const flush = () => {
    if (list.length) blocks.push(<ul key={`l${blocks.length}`} className="list-disc space-y-1 pl-6">{list.map((li, i) => <li key={i}>{inline(li)}</li>)}</ul>);
    if (para.length) {
      const text = para.join(" ");
      blocks.push(quote
        ? <p key={`q${blocks.length}`} className="rounded-xl border-l-8 border-amber-500 bg-amber-50 p-3 font-semibold dark:bg-amber-950">{inline(text)}</p>
        : <p key={`p${blocks.length}`}>{inline(text)}</p>);
    }
    list = [];
    para = [];
    quote = false;
  };
  for (const raw of md.split("\n")) {
    const line = raw.trimEnd();
    if (/^\s*- /.test(line)) { if (para.length) flush(); list.push(line.replace(/^\s*- /, "")); continue; }
    if (/^\s{2,}\S/.test(line) && list.length) { list[list.length - 1] += " " + line.trim(); continue; }
    if (line.startsWith("> ")) { if (!quote) flush(); quote = true; para.push(line.slice(2)); continue; }
    if (line.trim() && !line.startsWith("#") && !list.length && !quote) { para.push(line.trim()); continue; }
    flush();
    if (!line.trim()) continue;
    if (!line.startsWith("#")) { para.push(line.trim()); continue; }
    const k = `b${blocks.length}`;
    if (line.startsWith("# ")) blocks.push(<h1 key={k} className="text-3xl font-extrabold">{inline(line.slice(2))}</h1>);
    else if (line.startsWith("## ")) blocks.push(<h2 key={k} className="pt-2 text-2xl font-bold">{inline(line.slice(3))}</h2>);

  }
  flush();
  return blocks.map((b, i) => <Fragment key={i}>{b}</Fragment>);
}

export default function LegalPage() {
  const { t } = useTranslation();
  const { name } = useParams();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [error, setError] = useState<string | null>(null);
  useDocumentTitle(t(`legal.${name}`, { defaultValue: t("legal.title") }));
  useEffect(() => {
    setDoc(null);
    api<Doc>(`/legal/${name}`).then(setDoc).catch((e) => setError(errorMessage(t, e)));
  }, [name, t]);
  if (error) return <Alert>{error}</Alert>;
  if (!doc) return <Spinner label={t("app.loading")} />;
  return (
    <article className="space-y-3 text-lg">
      {doc.draft && <Alert kind="warning">{t("legal.draftNotice")}</Alert>}
      {render(doc.markdown)}
      <nav className="flex flex-wrap gap-4 pt-4 font-semibold">
        {["terms", "seller-agreement", "prohibited-items"].map((n) => <Link key={n} className="underline" to={`/legal/${n}`}>{t(`legal.${n}`)}</Link>)}
      </nav>
    </article>
  );
}
