# Trading Website

This Next.js app shares the same Supabase Postgres database as the Telegram bot.

## Environment Variables

Create `web/.env.local`:

```text
DATABASE_URL=your-supabase-postgres-url
WEB_SESSION_SECRET=your-long-random-session-secret
ADMIN_WEB_USERNAME=admin
ADMIN_WEB_PASSWORD=your-admin-password
```

Never expose `DATABASE_URL` to browser code. It is used only by server components
and server actions.

## Local Development

```powershell
cd web
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Telegram Login Flow

1. User completes registration in the Telegram bot.
2. User sends `/web` to the bot.
3. Bot returns a one-time code.
4. User opens `/login` on the website and submits the code.
5. Website creates an HTTP-only cookie session for the same `users.id`.

## Shared Database

The website automatically creates missing supporting tables:

- `telegram_link_codes`
- `user_activity`
- `paper_trading_accounts`
- `paper_orders`
- `watchlists`

The existing `users` and `deposits` tables remain shared with the bot.

## Deployment

Keep the Telegram bot deployed as its own Render service. Deploy this website as a
separate service, for example Vercel or Render, and point both services to the
same Supabase `DATABASE_URL`.
