import { headers } from "next/headers";
import { readSession } from "./session";

export async function getServerSession() { return readSession((await headers()).get("cookie")); }
export { defaultRoute, hasCapability } from "./session";
