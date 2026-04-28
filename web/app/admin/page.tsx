import Link from "next/link";

import { requireAdmin } from "@/lib/auth";
import { query } from "@/lib/db";
import { dateTime, money, text } from "@/lib/format";

export default async function AdminDashboardPage() {
  await requireAdmin();
  const stats = await query(`
    SELECT
      (SELECT COUNT(*) FROM users) AS total_users,
      (SELECT COUNT(*) FROM deposits WHERE status = 'pending') AS pending_deposits,
      (SELECT COUNT(*) FROM paper_orders) AS paper_orders,
      (SELECT COUNT(*) FROM user_activity) AS activity_events,
      (SELECT COALESCE(SUM(balance), 0) FROM users) AS total_balance
  `);
  const users = await query(`
    SELECT id, telegram_id, username, full_name, email, phone, country, status, balance, created_at
    FROM users
    ORDER BY created_at DESC
    LIMIT 8
  `);
  const deposits = await query(`
    SELECT d.id, d.crypto, d.amount, d.status, d.created_at, u.username, u.full_name
    FROM deposits d
    JOIN users u ON u.id = d.user_id
    ORDER BY d.created_at DESC
    LIMIT 8
  `);
  const stat = stats.rows[0];

  return (
    <main className="container">
      <h1>CRM Dashboard</h1>
      <section className="grid">
        <div className="card"><p className="muted">Users</p><p className="stat">{stat.total_users}</p></div>
        <div className="card"><p className="muted">Pending Deposits</p><p className="stat">{stat.pending_deposits}</p></div>
        <div className="card"><p className="muted">Paper Orders</p><p className="stat">{stat.paper_orders}</p></div>
        <div className="card"><p className="muted">Bot Balance</p><p className="stat">{money(stat.total_balance)}</p></div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <div className="actions">
          <h2 style={{ flex: 1 }}>Recent Users</h2>
          <Link className="button secondary" href="/admin/users">View All</Link>
        </div>
        <table>
          <thead><tr><th>User</th><th>Contact</th><th>Status</th><th>Balance</th><th>Created</th></tr></thead>
          <tbody>
            {users.rows.map((user) => (
              <tr key={user.id}>
                <td><Link href={`/admin/users/${user.id}`}><strong>{text(user.full_name)}</strong></Link><br /><span className="muted">@{text(user.username)}</span></td>
                <td>{text(user.email, "")}<br />{text(user.phone, "")}<br />{text(user.country, "")}</td>
                <td><span className="badge">{text(user.status, "active")}</span></td>
                <td>{money(user.balance)}</td>
                <td>{dateTime(user.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <div className="actions">
          <h2 style={{ flex: 1 }}>Recent Deposits</h2>
          <Link className="button secondary" href="/admin/deposits">Manage</Link>
        </div>
        <table>
          <thead><tr><th>ID</th><th>User</th><th>Crypto</th><th>Amount</th><th>Status</th><th>Date</th></tr></thead>
          <tbody>
            {deposits.rows.map((deposit) => (
              <tr key={deposit.id}>
                <td>#{deposit.id}</td>
                <td>{text(deposit.full_name)}<br /><span className="muted">@{text(deposit.username)}</span></td>
                <td>{deposit.crypto}</td>
                <td>{deposit.amount ? money(deposit.amount) : "Pending"}</td>
                <td><span className="badge">{deposit.status}</span></td>
                <td>{dateTime(deposit.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
