export default function PlansPage() {
  return (
    <main className="container">
      <h1>Plans</h1>
      <section className="grid">
        <div className="card">
          <h2>Demo</h2>
          <p className="stat">$0</p>
          <p className="muted">Telegram registration, dashboard, and paper trading.</p>
        </div>
        <div className="card">
          <h2>Pro</h2>
          <p className="stat">Soon</p>
          <p className="muted">Advanced signals, more watchlists, and live trading prep.</p>
        </div>
      </section>
    </main>
  );
}
