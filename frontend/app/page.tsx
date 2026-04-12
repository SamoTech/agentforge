import { redirect } from "next/navigation";

/**
 * Root page — redirect to the dashboard.
 * All UI lives under /dashboard to keep the app shell consistent.
 */
export default function RootPage() {
  redirect("/dashboard");
}
