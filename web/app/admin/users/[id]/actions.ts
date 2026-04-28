"use server";

import { redirect } from "next/navigation";

import { requireAdmin } from "@/lib/auth";
import { logActivity, query } from "@/lib/db";

export async function updateCrmUser(userId: number, formData: FormData) {
  await requireAdmin();
  const fields = {
    fullName: String(formData.get("full_name") || "").trim(),
    email: String(formData.get("email") || "").trim(),
    phone: String(formData.get("phone") || "").trim(),
    country: String(formData.get("country") || "").trim(),
    status: String(formData.get("status") || "active").trim(),
    adminNotes: String(formData.get("admin_notes") || "").trim(),
  };

  await query(
    `
    UPDATE users
    SET full_name = $1,
        email = $2,
        phone = $3,
        country = $4,
        status = $5,
        admin_notes = $6,
        updated_at = now()
    WHERE id = $7
    `,
    [
      fields.fullName || null,
      fields.email || null,
      fields.phone || null,
      fields.country || null,
      fields.status || "active",
      fields.adminNotes || null,
      userId,
    ],
  );
  await logActivity(userId, "admin", "crm_user_updated", { fields: Object.keys(fields) });
  redirect(`/admin/users/${userId}`);
}
