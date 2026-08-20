"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import type { AppSession } from "../../services/auth/session";

export function Nav() {
  const pathname = usePathname();
  const [session, setSession] = useState<AppSession | null>(null);
  useEffect(() => { let active = true; fetch("/api/auth/session", { cache: "no-store" }).then(async (response) => response.ok ? response.json() : null).then((payload) => { if (active) setSession(payload?.user ?? null); }); return () => { active = false; }; }, [pathname]);
  if (pathname === "/") return null;

  const links = [
    ...(session?.capabilities.includes("CANDIDATE") ? [["Candidate View", "/candidate"]] : []),
    ...(session?.capabilities.includes("HR") ? [["HR Control Center", "/hr"]] : []),
  ];

  async function logout() { await fetch("/api/auth/logout", { method: "POST" }); window.location.href = "/"; }

  return <header className="sticky top-0 z-40 border-b border-black/5 bg-white/90 backdrop-blur-xl"><div className="mx-auto flex max-w-[1440px] items-center justify-between gap-4 px-5 py-4 lg:px-10"><Link href={links[0]?.[1] ?? "/"} className="flex shrink-0 items-center gap-3 font-semibold tracking-[-0.02em]"><span className="grid h-9 w-9 place-items-center rounded-xl bg-[#173f35] text-xs text-white shadow-sm">D1</span><span className="hidden sm:inline">Day One Digital Twin</span></Link><div className="flex items-center gap-2"><nav aria-label="Available workspace" className="flex items-center gap-1 text-xs text-[#5e6965] sm:text-sm">{links.map(([label, href]) => <Link key={href} className={`rounded-full px-3 py-2 transition sm:px-4 ${pathname.startsWith(href) ? "bg-[#eef3ef] font-medium text-[#173f35]" : "hover:bg-black/[.03]"}`} href={href}>{label}</Link>)}</nav>{session && <div className="ml-2 hidden items-center gap-2 border-l border-black/10 pl-3 md:flex"><div className="text-right"><p className="text-xs font-medium">{session.name}</p><p className="text-[10px] text-[#89918e]">{session.capabilities[0] === "HR" ? "HR" : "STARTING EMPLOYEE"}</p></div><button onClick={logout} className="rounded-full border border-black/10 px-3 py-2 text-xs text-[#65706c] hover:bg-[#f4f6f4]">Sign out</button></div>}</div></div></header>;
}
