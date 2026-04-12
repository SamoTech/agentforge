import { redirect } from 'next/navigation'

/**
 * Root page — redirect straight to the dashboard.
 * Auth guard lives inside the dashboard layout.
 */
export default function RootPage() {
  redirect('/dashboard')
}
