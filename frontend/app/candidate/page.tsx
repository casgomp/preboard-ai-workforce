import type { Metadata } from "next";
import { CandidateDashboard } from "../../components/candidate/CandidateDashboard";
import { getServerSession, hasCapability } from "../../services/auth/server";
import { redirect } from "next/navigation";

export const metadata: Metadata = { title: "Anna’s Day One | Day One Digital Twin", description: "A calm, personalized view of Anna’s first-day readiness." };
export const dynamic = "force-dynamic";
export default async function CandidatePage() { const session = await getServerSession(); if (!session) redirect("/"); if (!hasCapability(session, "CANDIDATE") || !session.employeeId) redirect("/hr"); return <CandidateDashboard employeeId={session.employeeId} />; }
