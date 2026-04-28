import "server-only";

import { query } from "./db";

export async function ensurePaperAccount(userId: number) {
  const result = await query(
    `
    INSERT INTO paper_trading_accounts (user_id)
    VALUES ($1)
    ON CONFLICT (user_id) DO NOTHING
    RETURNING id, user_id, cash_balance, status, created_at, updated_at
    `,
    [userId],
  );

  if (result.rows[0]) {
    return result.rows[0];
  }

  const existing = await query(
    `
    SELECT id, user_id, cash_balance, status, created_at, updated_at
    FROM paper_trading_accounts
    WHERE user_id = $1
    `,
    [userId],
  );
  return existing.rows[0];
}

export async function listPaperOrders(userId: number, limit = 20) {
  const result = await query(
    `
    SELECT id, symbol, side, quantity, order_type, estimated_price, status, created_at
    FROM paper_orders
    WHERE user_id = $1
    ORDER BY created_at DESC
    LIMIT $2
    `,
    [userId, limit],
  );
  return result.rows;
}

export async function listWatchlist(userId: number) {
  const result = await query(
    `
    SELECT id, symbol, created_at
    FROM watchlists
    WHERE user_id = $1
    ORDER BY symbol ASC
    `,
    [userId],
  );
  return result.rows;
}
