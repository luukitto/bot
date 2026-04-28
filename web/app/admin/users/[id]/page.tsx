import Link from "next/link";
import { notFound } from "next/navigation";

import { requireAdmin } from "@/lib/auth";
import { query } from "@/lib/db";
import { dateTime, money, text } from "@/lib/format";

import { updateCrmUser } from "./actions";

export default async function AdminUserDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  await requireAdmin();
  const { id } = await params;
  const userId = Number(id);
  const userResult = await query("SELECT * FROM users WHERE id = $1", [userId]);
  const user = userResult.rows[0];
  if (!user) {
    notFound();
  }

  const deposits = await query(
    `
    SELECT id, crypto, amount, status, created_at
    FROM deposits
    WHERE user_id = $1
    ORDER BY created_at DESC
    LIMIT 20
    `,
    [userId],
  );
  const activity = await query(
    `
    SELECT actor_type, action, metadata, created_at
    FROM user_activity
    WHERE user_id = $1
    ORDER BY created_at DESC
    LIMIT 20
    `,
    [userId],
  );
  const updateAction = updateCrmUser.bind(null, userId);

  return (
    <main className="container">
      <div className="actions">
        <h1 style={{ flex: 1 }}>User #{user.id}</h1>
        <Link className="button secondary" href="/admin/users">Back</Link>
      </div>

      <section className="grid">
        <div className="card">
          <h2>Account</h2>
          <p><strong>Telegram ID:</strong> {user.telegram_id}</p>
          <p><strong>Username:</strong> @{text(user.username)}</p>
          <p><strong>Balance:</strong> {money(user.balance)}</p>
          <p><strong>Created:</strong> {dateTime(user.created_at)}</p>
        </div>
        <div className="card">
          <h2>CRM Info</h2>
          <p><strong>Name:</strong> {text(user.full_name)}</p>
          <p><strong>Email:</strong> {text(user.email)}</p>
          <p><strong>Phone:</strong> {text(user.phone)}</p>
          <p><strong>Country:</strong> {text(user.country)}</p>
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h2>Edit CRM Profile</h2>
        <form action={updateAction}>
          <div className="form-grid">
            <p><label>Full name</label><input name="full_name" defaultValue={text(user.full_name, "")} /></p>
            <p><label>Email</label><input name="email" type="email" defaultValue={text(user.email, "")} /></p>
            <p><label>Phone</label><input name="phone" defaultValue={text(user.phone, "")} /></p>
            <p><label>Country</label><input name="country" defaultValue={text(user.country, "")} /></p>
            <p>
              <label>Status</label>
              <select name="status" defaultValue={text(user.status, "active")}>
                <option value="active">Active</option>
                <option value="pending">Pending</option>
                <option value="blocked">Blocked</option>
              </select>
            </p>
          </div>
          <p><label>Admin notes</label><textarea name="admin_notes" defaultValue={text(user.admin_notes, "")} /></p>
          <button type="submit">Save CRM User</button>
        </form>
      </section>

      <section className="grid" style={{ marginTop: 18 }}>
        <div className="card">
          <h2>Deposits</h2>
          <table>
            <thead><tr><th>ID</th><th>Crypto</th><th>Amount</th><th>Status</th></tr></thead>
            <tbody>
              {deposits.rows.length ? deposits.rows.map((deposit) => (
                <tr key={deposit.id}>
                  <td>#{deposit.id}</td>
                  <td>{deposit.crypto}</td>
                  <td>{deposit.amount ? money(deposit.amount) : "Pending"}</td>
                  <td><span className="badge">{deposit.status}</span></td>
                </tr>
              )) : (
                <tr><td colSpan={4} className="muted">No deposits.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h2>Activity</h2>
          <table>
            <thead><tr><th>Actor</th><th>Action</th><th>Date</th></tr></thead>
            <tbody>
              {activity.rows.length ? activity.rows.map((event, index) => (
                <tr key={`${event.created_at}-${index}`}>
                  <td>{event.actor_type}</td>
                  <td>{event.action}</td>
                  <td>{dateTime(event.created_at)}</td>
                </tr>
              )) : (
                <tr><td colSpan={3} className="muted">No activity.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
