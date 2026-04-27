# Deploy on Render Free

This bot runs locally with SQLite. On Render, set `DATABASE_URL` and it will use Supabase Postgres.

## 1. Rotate your bot token

If your bot token was ever committed or shared, open BotFather and generate a new token.

## 2. Create Supabase database

1. Create a Supabase project.
2. Open **Project Settings -> Database**.
3. Copy the Postgres connection string.
4. Use the URI format that starts with `postgresql://`.
5. If Supabase shows an SSL option, keep `sslmode=require` in the URL.

## 3. Deploy to Render

1. Push this repo to GitHub.
2. In Render, choose **New -> Blueprint** or **New -> Web Service**.
3. Connect the GitHub repo.
4. Use the Docker environment if asked.
5. Choose the **Free** plan.

Render will use `render.yaml` for the service config.

## 4. Add Render environment variables

Add these in Render's **Environment** tab:

```text
BOT_TOKEN=your-new-telegram-bot-token
ADMIN_IDS=your_telegram_id
DATABASE_URL=your_supabase_postgres_connection_string
WEBHOOK_SECRET=any-long-random-string
```

You do not need to set `WEBHOOK_URL` on Render because the app reads Render's public URL automatically.

## 5. Keep the free service awake

Render free web services sleep after inactivity. Add a free UptimeRobot monitor that pings:

```text
https://your-render-app.onrender.com/health
```

Ping every 5 minutes.

## Admin commands

```text
/users
/addbalance <telegram_id> <amount>
/pending
/approve <deposit_id> <amount>
/reject <deposit_id>
```

Use a negative amount with `/addbalance` to remove funds:

```text
/addbalance 123456789 -25
```
