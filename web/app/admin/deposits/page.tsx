import Link from "next/link";

import { requireAdmin } from "@/lib/auth";
import { query } from "@/lib/db";
import { dateTime, money, text } from "@/lib/format";

import { approveDeposit, rejectDeposit } from "./actions";

export default async function AdminDepositsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  await requireAdmin();
  const { status: rawStatus } = await searchParams;
  const status = ["pending", "confirmed", "rejected"].includes(rawStatus || "")
    ? rawStatus
    : "";
  const deposits = status
    ? await query(
        `
        SELECT d.id, d.user_id, d.crypto, d.amount, d.status, d.created_at,
               u.username, u.full_name, u.telegram_id
        FROM deposits d
        JOIN users u ON u.id = d.user_id
        WHERE d.status = $1
        ORDER BY d.created_at DESC
        LIMIT 100
        `,
        [status],
      )
    : await query(`
        SELECT d.id, d.user_id, d.crypto, d.amount, d.status, d.created_at,
               u.username, u.full_name, u.telegram_id
        FROM deposits d
        JOIN users u ON u.id = d.user_id
        ORDER BY d.created_at DESC
        LIMIT 100
      `);

  return (
    <main className="container">
      <h1>CRM Deposits</h1>
      <section className="card actions">
        <Link className="button secondary" href="/admin/deposits">All</Link>
        <Link className="button secondary" href="/admin/deposits?status=pending">Pending</Link>
        <Link className="button secondary" href="/admin/deposits?status=confirmed">Confirmed</Link>
        <Link className="button secondary" href="/admin/deposits?status=rejected">Rejected</Link>
      </section>
      <section className="card" style={{ marginTop: 18 }}>
        <table>
          <thead><tr><th>ID</th><th>User</th><th>Crypto</th><th>Amount</th><th>Status</th><th>Date</th><th>Actions</th></tr></thead>
          <tbody>
            {deposits.rows.length ? deposits.rows.map((deposit) => {
              const approveAction = approveDeposit.bind(null, Number(deposit.id));
              const rejectAction = rejectDeposit.bind(null, Number(deposit.id));
              return (
                <tr key={deposit.id}>
                  <td>#{deposit.id}</td>
                  <td>
                    <Link href={`/admin/users/${deposit.user_id}`}>{text(deposit.full_name)}</Link>
                    <br />
                    <span className="muted">@{text(deposit.username)} / {deposit.telegram_id}</span>
                  </td>
                  <td>{deposit.crypto}</td>
                  <td>{deposit.amount ? money(deposit.amount) : "Pending"}</td>
                  <td><span className="badge">{deposit.status}</span></td>
                  <td>{dateTime(deposit.created_at)}</td>
                  <td>
                    {deposit.status === "pending" ? (
                      <div className="actions">
                        <form action={approveAction} className="actions">
                          <input
                            name="amount"
                            defaultValue={deposit.amount || ""}
                            placeholder="Amount"
                            style={{ width: 120 }}
                          />
                          <button type="submit">Approve</button>
                        </form>
                        <form action={rejectAction}>
                          <button className="danger" type="submit">Reject</button>
                        </form>
                      </div>
                    ) : (
                      <span className="muted">No action</span>
                    )}
                  </td>
                </tr>
              );
            }) : (
              <tr><td colSpan={7} className="muted">No deposits found.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
