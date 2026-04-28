import { loginWithTelegramCode } from "./actions";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const hasError = error === "invalid-code";

  return (
    <main className="container">
      <section className="card" style={{ margin: "40px auto", maxWidth: 520 }}>
        <h1>Login with Telegram</h1>
        <p className="muted">
          Open your Telegram bot and send <strong>/web</strong>. Paste the
          one-time code here to open your website dashboard.
        </p>
        {hasError ? (
          <p style={{ color: "#b91c1c", fontWeight: 700 }}>
            Code is invalid, expired, or already used.
          </p>
        ) : null}
        <form action={loginWithTelegramCode}>
          <p>
            <label>Telegram login code</label>
            <input name="code" placeholder="123456" required />
          </p>
          <button type="submit">Open Dashboard</button>
        </form>
      </section>
    </main>
  );
}
