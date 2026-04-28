import Link from "next/link";

import { requireUser } from "@/lib/auth";
import { query } from "@/lib/db";
import { dateTime, money, text } from "@/lib/format";
import { ensurePaperAccount, listPaperOrders, listWatchlist } from "@/lib/trading";

export default async function DashboardPage() {
  const user = await requireUser();
  const paperAccount = await ensurePaperAccount(Number(user.id));
  const orders = await listPaperOrders(Number(user.id), 5);
  const watchlist = await listWatchlist(Number(user.id));
  const deposits = await query(
    `
    SELECT id, crypto, amount, status, created_at
    FROM deposits
    WHERE user_id = $1
    ORDER BY created_at DESC
    LIMIT 5
    `,
    [user.id],
  );

  return (
    <main className="container">
      <h1>Dashboard</h1>
      <section className="grid">
        <div className="card">
          <p className="muted">Bot Balance</p>
          <p className="stat">{money(user.balance)}</p>
        </div>
        <div className="card">
          <p className="muted">Paper Cash</p>
          <p className="stat">{money(paperAccount.cash_balance)}</p>
        </div>
        <div className="card">
          <p className="muted">Status</p>
          <p className="stat">{text(user.status, "active")}</p>
        </div>
      </section>

      <section className="grid" style={{ marginTop: 18 }}>
        <div className="card">
          <div className="actions">
            <h2 style={{ flex: 1 }}>Profile</h2>
            <Link className="button secondary" href="/dashboard/profile">
              Edit
            </Link>
          </div>
          <p><strong>Name:</strong> {text(user.full_name)}</p>
          <p><strong>Telegram:</strong> @{text(user.username)}</p>
          <p><strong>Phone:</strong> {text(user.phone)}</p>
          <p><strong>Country:</strong> {text(user.country)}</p>
        </div>

        <div className="card">
          <div className="actions">
            <h2 style={{ flex: 1 }}>Watchlist</h2>
            <Link className="button secondary" href="/dashboard/watchlist">
              Manage
            </Link>
          </div>
          {watchlist.length ? (
            <p>{watchlist.map((item) => item.symbol).join(", ")}</p>
          ) : (
            <p className="muted">No symbols yet.</p>
          )}
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <div className="actions">
          <h2 style={{ flex: 1 }}>Recent Paper Orders</h2>
          <Link className="button secondary" href="/dashboard/paper-trading">
            Trade Demo
          </Link>
        </div>
        <table>
          <thead>
            <tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Status</th><th>Date</th></tr>
          </thead>
          <tbody>
            {orders.length ? orders.map((order) => (
              <tr key={order.id}>
                <td>{order.symbol}</td>
                <td>{order.side}</td>
                <td>{order.quantity}</td>
                <td><span className="badge">{order.status}</span></td>
                <td>{dateTime(order.created_at)}</td>
              </tr>
            )) : (
              <tr><td colSpan={5} className="muted">No paper orders yet.</td></tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h2>Recent Deposits</h2>
        <table>
          <thead>
            <tr><th>ID</th><th>Crypto</th><th>Amount</th><th>Status</th><th>Date</th></tr>
          </thead>
          <tbody>
            {deposits.rows.length ? deposits.rows.map((deposit) => (
              <tr key={deposit.id}>
                <td>#{deposit.id}</td>
                <td>{deposit.crypto}</td>
                <td>{deposit.amount ? money(deposit.amount) : "Pending"}</td>
                <td><span className="badge">{deposit.status}</span></td>
                <td>{dateTime(deposit.created_at)}</td>
              </tr>
            )) : (
              <tr><td colSpan={5} className="muted">No deposits yet.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
