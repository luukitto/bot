import Link from "next/link";

import { requireAdmin } from "@/lib/auth";
import { query } from "@/lib/db";
import { dateTime, money, text } from "@/lib/format";

export default async function AdminUsersPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  await requireAdmin();
  const { q: rawQuery } = await searchParams;
  const q = rawQuery?.trim() || "";
  const result = q
    ? await query(
        `
        SELECT id, telegram_id, username, full_name, email, phone, country, status, balance, created_at
        FROM users
        WHERE CAST(telegram_id AS TEXT) ILIKE $1
           OR COALESCE(username, '') ILIKE $1
           OR COALESCE(full_name, '') ILIKE $1
           OR COALESCE(email, '') ILIKE $1
           OR COALESCE(phone, '') ILIKE $1
        ORDER BY created_at DESC
        LIMIT 100
        `,
        [`%${q}%`],
      )
    : await query(`
        SELECT id, telegram_id, username, full_name, email, phone, country, status, balance, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 100
      `);

  return (
    <main className="container">
      <h1>CRM Users</h1>
      <section className="card">
        <form className="actions">
          <input
            name="q"
            defaultValue={q}
            placeholder="Search name, username, email, phone, Telegram ID"
            style={{ maxWidth: 420 }}
          />
          <button type="submit">Search</button>
          <Link className="button secondary" href="/admin/users">Clear</Link>
        </form>
      </section>
      <section className="card" style={{ marginTop: 18 }}>
        <table>
          <thead><tr><th>User</th><th>Contact</th><th>Status</th><th>Balance</th><th>Created</th><th></th></tr></thead>
          <tbody>
            {result.rows.length ? result.rows.map((user) => (
              <tr key={user.id}>
                <td><strong>{text(user.full_name)}</strong><br /><span className="muted">@{text(user.username)} / {user.telegram_id}</span></td>
                <td>{text(user.email, "")}<br />{text(user.phone, "")}<br />{text(user.country, "")}</td>
                <td><span className="badge">{text(user.status, "active")}</span></td>
                <td>{money(user.balance)}</td>
                <td>{dateTime(user.created_at)}</td>
                <td><Link className="button" href={`/admin/users/${user.id}`}>Open</Link></td>
              </tr>
            )) : (
              <tr><td colSpan={6} className="muted">No users found.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
