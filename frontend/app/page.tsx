import { LoginScreen } from "../components/auth/LoginScreen";
import { defaultRoute, getServerSession } from "../services/auth/server";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";
export default async function Home() { const session = await getServerSession(); if (session) redirect(defaultRoute(session)); return <LoginScreen />; }
