import { adminLogin } from "./actions";

export default async function AdminLoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;

  return (
    <main className="container">
      <section className="card" style={{ margin: "40px auto", maxWidth: 520 }}>
        <h1>CRM Admin Login</h1>
        <p className="muted">Use your admin website credentials from environment variables.</p>
        {error ? (
          <p style={{ color: "#b91c1c", fontWeight: 700 }}>Invalid admin login.</p>
        ) : null}
        <form action={adminLogin}>
          <p>
            <label>Username</label>
            <input name="username" autoComplete="username" required />
          </p>
          <p>
            <label>Password</label>
            <input name="password" type="password" autoComplete="current-password" required />
          </p>
          <button type="submit">Open CRM</button>
        </form>
      </section>
    </main>
  );
}
