"use server";

import { redirect } from "next/navigation";

import { requireUser } from "@/lib/auth";
import { logActivity, query } from "@/lib/db";

export async function addWatchSymbol(formData: FormData) {
  const user = await requireUser();
  const symbol = String(formData.get("symbol") || "").trim().toUpperCase();
  if (!symbol) {
    redirect("/dashboard/watchlist");
  }

  await query(
    `
    INSERT INTO watchlists (user_id, symbol)
    VALUES ($1, $2)
    ON CONFLICT (user_id, symbol) DO NOTHING
    `,
    [user.id, symbol],
  );
  await logActivity(Number(user.id), "user", "watchlist_symbol_added", { symbol });
  redirect("/dashboard/watchlist");
}

export async function removeWatchSymbol(formData: FormData) {
  const user = await requireUser();
  const symbol = String(formData.get("symbol") || "").trim().toUpperCase();

  await query(
    `
    DELETE FROM watchlists
    WHERE user_id = $1 AND symbol = $2
    `,
    [user.id, symbol],
  );
  await logActivity(Number(user.id), "user", "watchlist_symbol_removed", { symbol });
  redirect("/dashboard/watchlist");
}
