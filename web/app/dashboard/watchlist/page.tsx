import { requireUser } from "@/lib/auth";
import { dateTime } from "@/lib/format";
import { listWatchlist } from "@/lib/trading";

import { addWatchSymbol, removeWatchSymbol } from "./actions";

export default async function WatchlistPage() {
  const user = await requireUser();
  const watchlist = await listWatchlist(Number(user.id));

  return (
    <main className="container">
      <h1>Watchlist</h1>
      <section className="card">
        <form action={addWatchSymbol} className="actions">
          <input
            name="symbol"
            placeholder="AAPL, TSLA, BTCUSD"
            style={{ maxWidth: 280 }}
            required
          />
          <button type="submit">Add Symbol</button>
        </form>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <table>
          <thead>
            <tr><th>Symbol</th><th>Added</th><th></th></tr>
          </thead>
          <tbody>
            {watchlist.length ? watchlist.map((item) => (
              <tr key={item.id}>
                <td><strong>{item.symbol}</strong></td>
                <td>{dateTime(item.created_at)}</td>
                <td>
                  <form action={removeWatchSymbol}>
                    <input type="hidden" name="symbol" value={item.symbol} />
                    <button className="danger" type="submit">Remove</button>
                  </form>
                </td>
              </tr>
            )) : (
              <tr><td colSpan={3} className="muted">No watchlist symbols yet.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
