import type { Metadata } from "next";
import { HRDashboard } from "../../components/hr/HRDashboard";
import { getServerSession, hasCapability } from "../../services/auth/server";
import { redirect } from "next/navigation";

export const metadata: Metadata = { title: "HR Control Center | Day One Digital Twin", description: "Operational readiness and risk across every colleague starting soon." };
export const dynamic = "force-dynamic";
export default async function HRPage() { const session = await getServerSession(); if (!session) redirect("/"); if (!hasCapability(session, "HR")) redirect("/candidate"); return <HRDashboard />; }
