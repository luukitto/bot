"use server";

import { redirect } from "next/navigation";

import { setAdminSession, verifyAdminCredentials } from "@/lib/auth";
import { logActivity } from "@/lib/db";

export async function adminLogin(formData: FormData) {
  const username = String(formData.get("username") || "");
  const password = String(formData.get("password") || "");

  if (!(await verifyAdminCredentials(username, password))) {
    redirect("/admin/login?error=invalid");
  }

  await setAdminSession(username);
  await logActivity(null, "admin", "admin_login", { username });
  redirect("/admin");
}
