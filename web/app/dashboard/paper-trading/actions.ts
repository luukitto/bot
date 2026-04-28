"use server";

import { redirect } from "next/navigation";

import { requireUser } from "@/lib/auth";
import { logActivity, query } from "@/lib/db";
import { ensurePaperAccount } from "@/lib/trading";

export async function createPaperOrder(formData: FormData) {
  const user = await requireUser();
  await ensurePaperAccount(Number(user.id));

  const symbol = String(formData.get("symbol") || "").trim().toUpperCase();
  const side = String(formData.get("side") || "buy");
  const quantity = Number(formData.get("quantity") || 0);
  const estimatedPrice = Number(formData.get("estimated_price") || 0);

  if (!symbol || !["buy", "sell"].includes(side) || quantity <= 0) {
    redirect("/dashboard/paper-trading?error=invalid-order");
  }

  await query(
    `
    INSERT INTO paper_orders (user_id, symbol, side, quantity, order_type, estimated_price, status)
    VALUES ($1, $2, $3, $4, 'market', $5, 'filled')
    `,
    [
      user.id,
      symbol,
      side,
      quantity,
      Number.isFinite(estimatedPrice) && estimatedPrice > 0 ? estimatedPrice : null,
    ],
  );
  await query(
    `
    UPDATE paper_trading_accounts
    SET updated_at = now()
    WHERE user_id = $1
    `,
    [user.id],
  );
  await logActivity(Number(user.id), "user", "paper_order_created", {
    symbol,
    side,
    quantity,
    estimatedPrice,
  });

  redirect("/dashboard/paper-trading");
}
