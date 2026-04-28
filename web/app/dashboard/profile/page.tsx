import { requireUser } from "@/lib/auth";
import { dateTime, money, text } from "@/lib/format";

import { updateProfile } from "./actions";

export default async function ProfilePage() {
  const user = await requireUser();

  return (
    <main className="container">
      <h1>Profile</h1>
      <section className="card">
        <div className="grid">
          <p><strong>Name:</strong><br />{text(user.full_name)}</p>
          <p><strong>Telegram ID:</strong><br />{text(user.telegram_id)}</p>
          <p><strong>Username:</strong><br />@{text(user.username)}</p>
          <p><strong>Phone:</strong><br />{text(user.phone)}</p>
          <p><strong>Balance:</strong><br />{money(user.balance)}</p>
          <p><strong>Created:</strong><br />{dateTime(user.created_at)}</p>
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h2>Editable Website Info</h2>
        <form action={updateProfile}>
          <div className="form-grid">
            <p>
              <label>Email</label>
              <input name="email" type="email" defaultValue={text(user.email, "")} />
            </p>
            <p>
              <label>Country</label>
              <input name="country" defaultValue={text(user.country, "")} />
            </p>
          </div>
          <button type="submit">Save Profile</button>
        </form>
      </section>
    </main>
  );
}
