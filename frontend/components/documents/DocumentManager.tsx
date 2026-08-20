"use client";

import { useEffect, useState } from "react";
import type { CompanyDocument } from "../../services/documents/types";
import { DocumentQuestionBox } from "./DocumentQuestionBox";

export function DocumentManager() {
  const [documents, setDocuments] = useState<CompanyDocument[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const response = await fetch("/api/documents", { cache: "no-store" });
    const payload = await response.json();
    if (response.ok) setDocuments(payload.documents); else setError(payload.error);
  }

  useEffect(() => {
    let active = true;
    fetch("/api/documents", { cache: "no-store" })
      .then(async (response) => ({ response, payload: await response.json() }))
      .then(({ response, payload }) => { if (!active) return; if (response.ok) setDocuments(payload.documents); else setError(payload.error); });
    return () => { active = false; };
  }, []);

  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    const form = event.currentTarget;
    const response = await fetch("/api/documents", { method: "POST", body: new FormData(form) });
    const payload = await response.json();
    if (!response.ok) setError(payload.error ?? "Upload failed.");
    else {
      setNotice(`${payload.document.title} was extracted into ${payload.document.chunkCount} searchable passage${payload.document.chunkCount === 1 ? "" : "s"}.`);
      form.reset();
      await load();
    }
    setBusy(false);
  }

  return <section className="mt-6 rounded-[28px] border border-black/[.06] bg-white p-6 shadow-sm lg:p-8"><div className="grid gap-8 xl:grid-cols-[.85fr_1.15fr]"><div><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[#65736d]">Trusted knowledge</p><h2 className="mt-2 text-2xl font-semibold tracking-[-0.035em]">Company document library</h2><p className="mt-2 text-sm leading-6 text-[#6d7873]">Upload source documents, assign ownership and control whether candidates or only HR may retrieve them.</p><form onSubmit={upload} className="mt-6 grid gap-3"><input required name="title" placeholder="Document title" className="rounded-xl border border-black/10 px-4 py-3 text-sm outline-none focus:border-[#3c7460]" /><div className="grid grid-cols-2 gap-3"><input required name="department" placeholder="Department" className="rounded-xl border border-black/10 px-4 py-3 text-sm outline-none focus:border-[#3c7460]" /><select name="audience" className="rounded-xl border border-black/10 bg-white px-4 py-3 text-sm outline-none"><option value="ALL_EMPLOYEES">All employees</option><option value="HR_ONLY">HR only</option></select></div><div className="grid grid-cols-2 gap-3"><input required name="ownerName" placeholder="Owner name" className="rounded-xl border border-black/10 px-4 py-3 text-sm outline-none focus:border-[#3c7460]" /><input required name="ownerEmail" type="email" placeholder="Owner email" className="rounded-xl border border-black/10 px-4 py-3 text-sm outline-none focus:border-[#3c7460]" /></div><label className="rounded-xl border border-dashed border-black/15 bg-[#f7f8f6] p-4 text-xs text-[#65706c]">PDF, TXT, Markdown, CSV, JSON or HTML · max 5 MB<input required name="file" type="file" accept=".pdf,.txt,.md,.csv,.json,.html,text/plain,text/markdown,application/pdf" className="mt-2 block w-full text-xs file:mr-3 file:rounded-lg file:border-0 file:bg-[#e8f0eb] file:px-3 file:py-2 file:font-medium file:text-[#315e4b]" /></label>{error && <p role="alert" className="rounded-lg bg-[#fff0e8] p-3 text-xs text-[#914b2d]">{error}</p>}{notice && <p className="rounded-lg bg-[#eaf5ee] p-3 text-xs text-[#366a52]">{notice}</p>}<button disabled={busy} className="rounded-xl bg-[#173f35] px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Extracting document…" : "Upload and extract"}</button></form></div><div><div className="flex items-center justify-between"><h3 className="font-semibold">Indexed documents</h3><span className="rounded-full bg-[#eef3ef] px-3 py-1 text-xs text-[#547067]">{documents.length} ready</span></div><div className="mt-4 max-h-72 space-y-2 overflow-auto pr-1">{documents.map((document) => <article key={document.id} className="flex items-start justify-between gap-4 rounded-xl border border-black/[.05] bg-[#fafbfa] p-3"><div><p className="text-sm font-medium">{document.title}</p><p className="mt-1 text-[11px] text-[#84908a]">{document.department} · {document.ownerName} · {document.chunkCount} passages</p></div><span className={`rounded-full px-2 py-1 text-[9px] font-semibold ${document.audience === "HR_ONLY" ? "bg-[#f3e9df] text-[#875c3e]" : "bg-[#e8f2ec] text-[#37664f]"}`}>{document.audience === "HR_ONLY" ? "HR ONLY" : "ALL EMPLOYEES"}</span></article>)}</div><div className="mt-6 border-t border-black/[.06] pt-6"><h3 className="font-semibold">Test the grounded answer</h3><p className="mt-1 text-xs text-[#7a8580]">HR can search both employee-safe and HR-only documents.</p><DocumentQuestionBox variant="light" compact scope="hr" /></div></div></div></section>;
}
