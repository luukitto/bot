"use server";

import { redirect } from "next/navigation";

import { requireUser } from "@/lib/auth";
import { logActivity, query } from "@/lib/db";

export async function updateProfile(formData: FormData) {
  const user = await requireUser();
  const email = String(formData.get("email") || "").trim();
  const country = String(formData.get("country") || "").trim();

  await query(
    `
    UPDATE users
    SET email = $1, country = $2, updated_at = now()
    WHERE id = $3
    `,
    [email || null, country || null, user.id],
  );
  await logActivity(Number(user.id), "user", "profile_updated", {
    fields: ["email", "country"],
  });

  redirect("/dashboard/profile");
}
