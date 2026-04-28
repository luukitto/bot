import { requireUser } from "@/lib/auth";
import { dateTime, money } from "@/lib/format";
import { listPaperOrders } from "@/lib/trading";

export default async function OrdersPage() {
  const user = await requireUser();
  const orders = await listPaperOrders(Number(user.id), 100);

  return (
    <main className="container">
      <h1>Paper Order History</h1>
      <section className="card">
        <table>
          <thead><tr><th>ID</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Type</th><th>Price</th><th>Status</th><th>Date</th></tr></thead>
          <tbody>
            {orders.length ? orders.map((order) => (
              <tr key={order.id}>
                <td>#{order.id}</td>
                <td>{order.symbol}</td>
                <td>{order.side}</td>
                <td>{order.quantity}</td>
                <td>{order.order_type}</td>
                <td>{order.estimated_price ? money(order.estimated_price) : "N/A"}</td>
                <td><span className="badge">{order.status}</span></td>
                <td>{dateTime(order.created_at)}</td>
              </tr>
            )) : (
              <tr><td colSpan={8} className="muted">No paper orders yet.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
