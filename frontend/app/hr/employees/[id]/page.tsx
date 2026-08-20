import type { Metadata } from "next";
import { EmployeeDetail } from "../../../../components/hr/EmployeeDetail";
import { employees } from "../../../../data/demo/seed";
import { getServerSession, hasCapability } from "../../../../services/auth/server";
import { redirect } from "next/navigation";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const session = await getServerSession();
  if (!hasCapability(session, "HR")) {
    const title = "Employee Readiness | Day One Digital Twin";
    const description = "Authorized HR access is required.";
    return { title, description, openGraph: { title, description, images: [] }, twitter: { title, description, images: [] } };
  }
  const { id } = await params;
  const employee = employees.find((item) => item.id === id);
  const title = employee ? `${employee.name} Readiness | Day One Digital Twin` : "Employee Readiness | Day One Digital Twin";
  const description = employee ? `Explainable Day One readiness, fact provenance and operational risk for ${employee.name}.` : "Explainable fact provenance, readiness contribution and operational risk.";
  return { title, description, openGraph: { title, description, images: [] }, twitter: { title, description, images: [] } };
}
export default async function EmployeePage({ params }: { params: Promise<{ id: string }> }) { const session = await getServerSession(); if (!session) redirect("/"); if (!hasCapability(session, "HR")) redirect("/candidate"); const { id } = await params; return <EmployeeDetail employeeId={id} />; }
