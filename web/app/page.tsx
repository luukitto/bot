import Link from "next/link";

export default function HomePage() {
  return (
    <main className="container">
      <section className="hero">
        <p className="muted">Telegram-connected trading dashboard</p>
        <h1>Monitor users, CRM data, and paper trading in one website.</h1>
        <p>
          This MVP shares the same Supabase database as your Telegram bot, so
          user registration data, deposits, balances, and CRM notes stay in one
          place.
        </p>
        <div className="actions">
          <Link className="button" href="/login">
            Login with Telegram Code
          </Link>
          <Link className="button secondary" href="/admin">
            Open CRM
          </Link>
        </div>
      </section>

      <section className="grid" style={{ marginTop: 24 }}>
        <div className="card">
          <h2>Shared Supabase</h2>
          <p className="muted">
            The website and bot read the same users, deposits, and CRM fields.
          </p>
        </div>
        <div className="card">
          <h2>Paper Trading First</h2>
          <p className="muted">
            Demo accounts and mock order execution are ready before live trading.
          </p>
        </div>
        <div className="card">
          <h2>CRM Monitoring</h2>
          <p className="muted">
            Admins can review profiles, deposit status, and user activity.
          </p>
        </div>
      </section>
    </main>
  );
}
