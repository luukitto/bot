"use server";

import { redirect } from "next/navigation";

import { consumeTelegramCode } from "@/lib/auth";

export async function loginWithTelegramCode(formData: FormData) {
  const code = String(formData.get("code") || "").trim();
  const userId = await consumeTelegramCode(code);

  if (!userId) {
    redirect("/login?error=invalid-code");
  }

  redirect("/dashboard");
}
