import Link from "next/link";

import { requireAdmin } from "@/lib/auth";
import { query } from "@/lib/db";
import { dateTime, text } from "@/lib/format";

export default async function AdminActivityPage() {
  await requireAdmin();
  const activity = await query(`
    SELECT a.id, a.user_id, a.actor_type, a.action, a.metadata, a.created_at,
           u.username, u.full_name
    FROM user_activity a
    LEFT JOIN users u ON u.id = a.user_id
    ORDER BY a.created_at DESC
    LIMIT 200
  `);

  return (
    <main className="container">
      <h1>Activity Timeline</h1>
      <section className="card">
        <table>
          <thead><tr><th>When</th><th>Actor</th><th>User</th><th>Action</th><th>Metadata</th></tr></thead>
          <tbody>
            {activity.rows.length ? activity.rows.map((event) => (
              <tr key={event.id}>
                <td>{dateTime(event.created_at)}</td>
                <td><span className="badge">{event.actor_type}</span></td>
                <td>
                  {event.user_id ? (
                    <Link href={`/admin/users/${event.user_id}`}>{text(event.full_name, `User #${event.user_id}`)}</Link>
                  ) : (
                    <span className="muted">System</span>
                  )}
                  <br />
                  <span className="muted">@{text(event.username)}</span>
                </td>
                <td>{event.action}</td>
                <td><code>{JSON.stringify(event.metadata || {})}</code></td>
              </tr>
            )) : (
              <tr><td colSpan={5} className="muted">No activity yet.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
