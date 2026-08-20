"use client";

import { useState } from "react";

const demos = [
  { label: "Starting employee", name: "Anna", email: "anna.mueller@dayone.demo", password: "Welcome5!" },
  { label: "HR partner", name: "Sarah", email: "sarah.weber@dayone.demo", password: "PeopleOps!" },
];

export function LoginScreen() {
  const [email, setEmail] = useState(demos[0].email);
  const [password, setPassword] = useState(demos[0].password);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function signIn(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    const response = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
    const payload = await response.json();
    if (!response.ok) { setError(payload.error ?? "Unable to sign in."); setBusy(false); return; }
    window.location.href = payload.redirectTo;
  }

  return <main className="min-h-screen bg-[#10251f] text-white"><div className="grid min-h-screen lg:grid-cols-[1.08fr_.92fr]"><section className="flex flex-col justify-between overflow-hidden p-7 sm:p-12 lg:p-16"><div className="flex items-center gap-3 font-semibold"><span className="grid h-10 w-10 place-items-center rounded-xl bg-[#b9d9c8] text-xs text-[#173f35]">D1</span>Day One Digital Twin</div><div className="relative my-20 max-w-2xl"><div className="pointer-events-none absolute -left-24 -top-28 h-72 w-72 rounded-full border border-white/10" /><p className="text-xs font-semibold uppercase tracking-[.18em] text-[#9ec4b3]">One trusted readiness picture</p><h1 className="mt-5 text-5xl font-semibold tracking-[-0.055em] sm:text-7xl">Ready for what comes next.</h1><p className="mt-6 max-w-xl text-lg leading-8 text-white/60">Sign in to open either your Day One preparation or the HR control center.</p></div><p className="text-xs text-white/35">Each demo account has one clear workspace.</p></section><section className="flex items-center bg-[#f5f6f2] p-6 text-[#17231f] sm:p-12"><div className="mx-auto w-full max-w-md"><p className="text-xs font-semibold uppercase tracking-[.17em] text-[#6b7b74]">Local demo access</p><h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em]">Welcome back</h2><p className="mt-2 text-sm leading-6 text-[#71807a]">Choose a local demo account or enter its credentials.</p><form className="mt-8 space-y-4" onSubmit={signIn}><label className="block text-sm font-medium">Work email<input value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="username" className="mt-2 w-full rounded-xl border border-black/10 bg-white px-4 py-3.5 outline-none transition focus:border-[#3c7460] focus:ring-4 focus:ring-[#3c7460]/10" /></label><label className="block text-sm font-medium">Password<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" className="mt-2 w-full rounded-xl border border-black/10 bg-white px-4 py-3.5 outline-none transition focus:border-[#3c7460] focus:ring-4 focus:ring-[#3c7460]/10" /></label>{error && <p role="alert" className="rounded-lg bg-[#fff0e8] px-3 py-2 text-xs text-[#9a4c2b]">{error}</p>}<button disabled={busy} className="w-full rounded-xl bg-[#173f35] px-4 py-3.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#0f3028] disabled:opacity-60">{busy ? "Signing in…" : "Sign in"}</button></form><div className="mt-7 rounded-2xl border border-black/[.06] bg-white p-4"><div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[.12em] text-[#71807a]">Demo access</p><span className="rounded-full bg-[#eef3ef] px-2 py-1 text-[10px] font-medium text-[#3f6c59]">2 profiles</span></div><div className="mt-3 grid gap-2 text-xs text-[#64716c]">{demos.map((demo) => <button key={demo.email} type="button" onClick={() => { setEmail(demo.email); setPassword(demo.password); setError(""); }} className="flex justify-between rounded-lg bg-[#f6f8f6] p-2 text-left hover:bg-[#eef3ef]"><span>{demo.label}</span><strong>{demo.name}</strong></button>)}</div></div></div></section></div></main>;
}
