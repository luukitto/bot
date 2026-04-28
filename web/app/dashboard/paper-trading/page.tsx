import Link from "next/link";

import { requireUser } from "@/lib/auth";
import { dateTime, money } from "@/lib/format";
import { ensurePaperAccount, listPaperOrders } from "@/lib/trading";

import { createPaperOrder } from "./actions";

export default async function PaperTradingPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const user = await requireUser();
  const account = await ensurePaperAccount(Number(user.id));
  const orders = await listPaperOrders(Number(user.id), 20);

  return (
    <main className="container">
      <div className="actions">
        <h1 style={{ flex: 1 }}>Paper Trading</h1>
        <Link className="button secondary" href="/dashboard/orders">Order History</Link>
      </div>
      <section className="grid">
        <div className="card">
          <p className="muted">Demo Cash Balance</p>
          <p className="stat">{money(account.cash_balance)}</p>
        </div>
        <div className="card">
          <p className="muted">Account Status</p>
          <p className="stat">{account.status}</p>
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h2>Mock Market Order</h2>
        <p className="muted">
          This records a demo order only. It does not send real money or live
          orders to Alpaca yet.
        </p>
        {error ? (
          <p style={{ color: "#b91c1c", fontWeight: 700 }}>Please enter a valid order.</p>
        ) : null}
        <form action={createPaperOrder}>
          <div className="form-grid">
            <p><label>Symbol</label><input name="symbol" placeholder="AAPL" required /></p>
            <p>
              <label>Side</label>
              <select name="side" defaultValue="buy">
                <option value="buy">Buy</option>
                <option value="sell">Sell</option>
              </select>
            </p>
            <p><label>Quantity</label><input name="quantity" type="number" min="0.0001" step="0.0001" required /></p>
            <p><label>Estimated Price</label><input name="estimated_price" type="number" min="0" step="0.01" placeholder="Optional" /></p>
          </div>
          <button type="submit">Submit Demo Order</button>
        </form>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h2>Recent Orders</h2>
        <table>
          <thead><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>Status</th><th>Date</th></tr></thead>
          <tbody>
            {orders.length ? orders.map((order) => (
              <tr key={order.id}>
                <td>{order.symbol}</td>
                <td>{order.side}</td>
                <td>{order.quantity}</td>
                <td>{order.estimated_price ? money(order.estimated_price) : "N/A"}</td>
                <td><span className="badge">{order.status}</span></td>
                <td>{dateTime(order.created_at)}</td>
              </tr>
            )) : (
              <tr><td colSpan={6} className="muted">No paper orders yet.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
