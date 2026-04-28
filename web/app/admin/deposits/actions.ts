"use server";

import { redirect } from "next/navigation";

import { requireAdmin } from "@/lib/auth";
import { logActivity, query } from "@/lib/db";

export async function approveDeposit(depositId: number, formData: FormData) {
  await requireAdmin();
  const amount = Number(formData.get("amount") || 0);
  if (!Number.isFinite(amount) || amount <= 0) {
    redirect("/admin/deposits?status=pending");
  }

  const deposit = await query(
    "SELECT id, user_id, status FROM deposits WHERE id = $1",
    [depositId],
  );
  const row = deposit.rows[0];
  if (row?.status === "pending") {
    await query(
      "UPDATE deposits SET status = 'confirmed', amount = $1 WHERE id = $2",
      [amount, depositId],
    );
    await query("UPDATE users SET balance = balance + $1 WHERE id = $2", [
      amount,
      row.user_id,
    ]);
    await logActivity(Number(row.user_id), "admin", "deposit_approved", {
      depositId,
      amount,
    });
  }

  redirect("/admin/deposits?status=pending");
}

export async function rejectDeposit(depositId: number) {
  await requireAdmin();
  const deposit = await query(
    "SELECT id, user_id, status FROM deposits WHERE id = $1",
    [depositId],
  );
  const row = deposit.rows[0];
  if (row?.status === "pending") {
    await query("UPDATE deposits SET status = 'rejected' WHERE id = $1", [depositId]);
    await logActivity(Number(row.user_id), "admin", "deposit_rejected", { depositId });
  }

  redirect("/admin/deposits?status=pending");
}
