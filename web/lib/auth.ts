import "server-only";
import crypto from "crypto";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { logActivity, query } from "./db";

const USER_SESSION_COOKIE = "trading_user_session";
const ADMIN_SESSION_COOKIE = "trading_admin_session";
const SESSION_TTL_SECONDS = 60 * 60 * 12;

function sessionSecret() {
  const secret = process.env.WEB_SESSION_SECRET || process.env.ADMIN_SESSION_SECRET;
  if (!secret) {
    throw new Error("WEB_SESSION_SECRET or ADMIN_SESSION_SECRET is required.");
  }
  return secret;
}

function sign(payload: string) {
  return crypto
    .createHmac("sha256", sessionSecret())
    .update(payload)
    .digest("hex");
}

function secureCompare(left: string, right: string) {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);
  if (leftBuffer.length !== rightBuffer.length) {
    return false;
  }
  return crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function createToken(subject: string) {
  const expiresAt = Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS;
  const payload = `${subject}:${expiresAt}`;
  return `${payload}:${sign(payload)}`;
}

function verifyToken(token?: string) {
  if (!token) {
    return null;
  }

  const parts = token.split(":");
  if (parts.length < 3) {
    return null;
  }

  const signature = parts.pop();
  const expiresAtRaw = parts.pop();
  const subject = parts.join(":");
  const payload = `${subject}:${expiresAtRaw}`;
  const expected = sign(payload);
  const expiresAt = Number(expiresAtRaw);

  if (!signature || !Number.isFinite(expiresAt) || expiresAt < Date.now() / 1000) {
    return null;
  }

  return secureCompare(signature, expected) ? subject : null;
}

export async function setUserSession(userId: number) {
  const cookieStore = await cookies();
  cookieStore.set(USER_SESSION_COOKIE, createToken(`user:${userId}`), {
    httpOnly: true,
    sameSite: "lax",
    maxAge: SESSION_TTL_SECONDS,
    path: "/",
  });
}

export async function setAdminSession(username: string) {
  const cookieStore = await cookies();
  cookieStore.set(ADMIN_SESSION_COOKIE, createToken(`admin:${username}`), {
    httpOnly: true,
    sameSite: "lax",
    maxAge: SESSION_TTL_SECONDS,
    path: "/",
  });
}

export async function clearSessions() {
  const cookieStore = await cookies();
  cookieStore.delete(USER_SESSION_COOKIE);
  cookieStore.delete(ADMIN_SESSION_COOKIE);
}

export async function getCurrentUser() {
  const cookieStore = await cookies();
  const subject = verifyToken(cookieStore.get(USER_SESSION_COOKIE)?.value);
  if (!subject?.startsWith("user:")) {
    return null;
  }

  const userId = Number(subject.replace("user:", ""));
  if (!Number.isInteger(userId)) {
    return null;
  }

  const result = await query(
    `
    SELECT id, telegram_id, username, balance, full_name, email, phone, country,
           status, admin_notes, created_at, updated_at
    FROM users
    WHERE id = $1
    `,
    [userId],
  );

  return result.rows[0] ?? null;
}

export async function requireUser() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }
  return user;
}

export async function isAdminLoggedIn() {
  const cookieStore = await cookies();
  const subject = verifyToken(cookieStore.get(ADMIN_SESSION_COOKIE)?.value);
  return subject === `admin:${process.env.ADMIN_WEB_USERNAME || "admin"}`;
}

export async function requireAdmin() {
  if (!(await isAdminLoggedIn())) {
    redirect("/admin/login");
  }
}

export async function consumeTelegramCode(code: string) {
  const normalizedCode = code.trim();
  const result = await query(
    `
    UPDATE telegram_link_codes
    SET used_at = now()
    WHERE code = $1
      AND used_at IS NULL
      AND expires_at > now()
    RETURNING user_id
    `,
    [normalizedCode],
  );

  const row = result.rows[0];
  if (!row) {
    return null;
  }

  await setUserSession(Number(row.user_id));
  await logActivity(Number(row.user_id), "user", "website_login", {
    method: "telegram_code",
  });
  return Number(row.user_id);
}

export async function verifyAdminCredentials(username: string, password: string) {
  const expectedUsername = process.env.ADMIN_WEB_USERNAME || "admin";
  const expectedPassword = process.env.ADMIN_WEB_PASSWORD || "";

  if (!expectedPassword) {
    return false;
  }

  return (
    secureCompare(username, expectedUsername) &&
    secureCompare(password, expectedPassword)
  );
}
