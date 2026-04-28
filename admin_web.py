import hashlib
import hmac
import time
from html import escape
from urllib.parse import urlencode

from aiohttp import web

import database as db
from config import ADMIN_SESSION_SECRET, ADMIN_WEB_PASSWORD, ADMIN_WEB_USERNAME

SESSION_COOKIE = "admin_session"
SESSION_TTL_SECONDS = 60 * 60 * 12
CRM_STATUSES = ("active", "pending", "blocked")


def setup_admin_routes(app: web.Application, bot=None):
    app["bot"] = bot
    app.router.add_get("/admin", dashboard)
    app.router.add_get("/admin/", dashboard)
    app.router.add_get("/admin/login", login_page)
    app.router.add_post("/admin/login", login_submit)
    app.router.add_post("/admin/logout", logout)
    app.router.add_get("/admin/users", users_page)
    app.router.add_get(r"/admin/users/{user_id:\d+}", user_detail_page)
    app.router.add_post(r"/admin/users/{user_id:\d+}", user_update_submit)
    app.router.add_get("/admin/deposits", deposits_page)
    app.router.add_post(r"/admin/deposits/{deposit_id:\d+}/approve", approve_deposit)
    app.router.add_post(r"/admin/deposits/{deposit_id:\d+}/reject", reject_deposit)


def sign_session(username: str, expires_at: int) -> str:
    payload = f"{username}:{expires_at}"
    signature = hmac.new(
        ADMIN_SESSION_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{signature}"


def is_valid_session(cookie_value: str | None) -> bool:
    if not cookie_value or not ADMIN_SESSION_SECRET:
        return False

    try:
        username, expires_at_raw, signature = cookie_value.split(":", 2)
        expires_at = int(expires_at_raw)
    except ValueError:
        return False

    if username != ADMIN_WEB_USERNAME or expires_at < int(time.time()):
        return False

    expected = sign_session(username, expires_at).rsplit(":", 1)[1]
    return hmac.compare_digest(signature, expected)


def require_admin(request: web.Request):
    if not is_valid_session(request.cookies.get(SESSION_COOKIE)):
        next_url = request.rel_url.path_qs
        raise web.HTTPFound(f"/admin/login?{urlencode({'next': next_url})}")


def redirect(location: str) -> web.Response:
    raise web.HTTPFound(location)


def html_response(body: str, *, title: str = "Admin CRM") -> web.Response:
    return web.Response(
        text=layout(body, title=title),
        content_type="text/html",
        charset="utf-8",
    )


def layout(body: str, *, title: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{ color-scheme: light; font-family: Arial, sans-serif; }}
    body {{ margin: 0; background: #f5f7fb; color: #18202f; }}
    header {{ background: #111827; color: #fff; padding: 16px 24px; }}
    nav a, nav button {{ color: #fff; margin-right: 16px; }}
    nav form {{ display: inline; }}
    main {{ max-width: 1180px; margin: 24px auto; padding: 0 16px; }}
    .card {{ background: #fff; border: 1px solid #dce1ea; border-radius: 10px; padding: 20px; margin-bottom: 18px; box-shadow: 0 1px 2px rgba(0,0,0,.04); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; }}
    .stat {{ font-size: 28px; font-weight: 700; margin-top: 8px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ border-bottom: 1px solid #e5e9f0; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ color: #48556a; font-size: 13px; text-transform: uppercase; }}
    input, textarea, select {{ width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #cdd5df; border-radius: 8px; }}
    textarea {{ min-height: 120px; }}
    label {{ display: block; font-weight: 700; margin-bottom: 6px; }}
    .form-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
    .actions {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
    button, .button {{ background: #2563eb; border: 0; color: #fff; padding: 10px 14px; border-radius: 8px; cursor: pointer; text-decoration: none; display: inline-block; }}
    .button-secondary {{ background: #475569; }}
    .button-danger {{ background: #dc2626; }}
    .muted {{ color: #64748b; }}
    .error {{ color: #b91c1c; font-weight: 700; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 3px 9px; background: #e0e7ff; color: #3730a3; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <nav>
      <strong>Trading Bot CRM</strong>
      <a href="/admin">Dashboard</a>
      <a href="/admin/users">Users</a>
      <a href="/admin/deposits">Deposits</a>
      <form method="post" action="/admin/logout"><button class="button-secondary" type="submit">Logout</button></form>
    </nav>
  </header>
  <main>{body}</main>
</body>
</html>"""


def format_money(value) -> str:
    return f"${float(value or 0):,.2f}"


def text_value(value) -> str:
    return escape(str(value)) if value is not None else ""


def selected(current: str | None, expected: str) -> str:
    return " selected" if (current or "active") == expected else ""


def login_form(error: str = "", next_url: str = "/admin") -> str:
    error_html = f'<p class="error">{escape(error)}</p>' if error else ""
    return f"""
<div class="card" style="max-width: 420px; margin: 60px auto;">
  <h1>Admin Login</h1>
  <p class="muted">Sign in to manage users, contact info, and deposits.</p>
  {error_html}
  <form method="post" action="/admin/login">
    <input type="hidden" name="next" value="{escape(next_url)}">
    <p><label>Username</label><input name="username" autocomplete="username" required></p>
    <p><label>Password</label><input name="password" type="password" autocomplete="current-password" required></p>
    <button type="submit">Login</button>
  </form>
</div>"""


async def login_page(request: web.Request) -> web.Response:
    if is_valid_session(request.cookies.get(SESSION_COOKIE)):
        redirect("/admin")
    return html_response(
        login_form(next_url=request.query.get("next", "/admin")),
        title="Admin Login",
    )


async def login_submit(request: web.Request) -> web.Response:
    form = await request.post()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    next_url = str(form.get("next", "/admin") or "/admin")

    if not next_url.startswith("/admin"):
        next_url = "/admin"

    if not ADMIN_WEB_PASSWORD or not ADMIN_SESSION_SECRET:
        return html_response(
            login_form(
                "Admin web password/session secret is not configured.",
                next_url=next_url,
            ),
            title="Admin Login",
        )

    valid_username = hmac.compare_digest(username, ADMIN_WEB_USERNAME)
    valid_password = hmac.compare_digest(password, ADMIN_WEB_PASSWORD)
    if not valid_username or not valid_password:
        return html_response(
            login_form("Invalid username or password.", next_url=next_url),
            title="Admin Login",
        )

    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    response = web.HTTPFound(next_url)
    response.set_cookie(
        SESSION_COOKIE,
        sign_session(username, expires_at),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="Lax",
    )
    raise response


async def logout(request: web.Request) -> web.Response:
    response = web.HTTPFound("/admin/login")
    response.del_cookie(SESSION_COOKIE)
    raise response


async def dashboard(request: web.Request) -> web.Response:
    require_admin(request)
    stats = await db.get_dashboard_stats()
    recent_users = await db.list_crm_users(limit=5)
    pending_deposits = await db.list_deposits(status="pending", limit=5)

    recent_rows = "".join(user_row(user) for user in recent_users)
    deposit_rows = "".join(deposit_row(item) for item in pending_deposits)
    body = f"""
<h1>CRM Dashboard</h1>
<section class="grid">
  <div class="card"><div class="muted">Total Users</div><div class="stat">{stats.get('total_users', 0)}</div></div>
  <div class="card"><div class="muted">Pending Deposits</div><div class="stat">{stats.get('pending_deposits', 0)}</div></div>
  <div class="card"><div class="muted">Total Balance</div><div class="stat">{format_money(stats.get('total_balance'))}</div></div>
</section>
<section class="card">
  <div class="actions"><h2 style="flex:1;">Recent Users</h2><a class="button" href="/admin/users">View all</a></div>
  <table><thead><tr><th>User</th><th>Contact</th><th>Status</th><th>Balance</th><th></th></tr></thead><tbody>{recent_rows or empty_row(5)}</tbody></table>
</section>
<section class="card">
  <div class="actions"><h2 style="flex:1;">Pending Deposits</h2><a class="button" href="/admin/deposits">Manage</a></div>
  <table><thead><tr><th>ID</th><th>User</th><th>Crypto</th><th>Amount</th><th>Status</th></tr></thead><tbody>{deposit_rows or empty_row(5)}</tbody></table>
</section>"""
    return html_response(body, title="CRM Dashboard")


async def users_page(request: web.Request) -> web.Response:
    require_admin(request)
    search = request.query.get("q", "")
    users = await db.list_crm_users(search=search, limit=100)
    rows = "".join(user_row(user) for user in users)
    body = f"""
<h1>Users</h1>
<section class="card">
  <form method="get" action="/admin/users" class="actions">
    <input style="max-width: 420px;" name="q" value="{escape(search)}" placeholder="Search username, name, email, phone, Telegram ID">
    <button type="submit">Search</button>
    <a class="button button-secondary" href="/admin/users">Clear</a>
  </form>
</section>
<section class="card">
  <table><thead><tr><th>User</th><th>Contact</th><th>Status</th><th>Balance</th><th></th></tr></thead><tbody>{rows or empty_row(5)}</tbody></table>
</section>"""
    return html_response(body, title="CRM Users")


async def user_detail_page(request: web.Request) -> web.Response:
    require_admin(request)
    user_id = int(request.match_info["user_id"])
    user = await db.get_user_by_id(user_id)
    if not user:
        raise web.HTTPNotFound(text="User not found")

    deposits = await db.get_user_deposits_by_id(user_id, limit=20)
    deposit_rows = "".join(simple_deposit_row(item) for item in deposits)
    status_options = "".join(
        f'<option value="{status}"{selected(user.get("status"), status)}>{status.title()}</option>'
        for status in CRM_STATUSES
    )
    body = f"""
<div class="actions"><h1 style="flex:1;">User #{user['id']}</h1><a class="button button-secondary" href="/admin/users">Back to users</a></div>
<section class="card">
  <h2>Account</h2>
  <p><strong>Telegram ID:</strong> {text_value(user.get('telegram_id'))}</p>
  <p><strong>Username:</strong> @{text_value(user.get('username')) or 'N/A'}</p>
  <p><strong>Balance:</strong> {format_money(user.get('balance'))}</p>
  <p><strong>Created:</strong> {text_value(user.get('created_at'))}</p>
</section>
<section class="card">
  <h2>CRM Profile</h2>
  <form method="post" action="/admin/users/{user['id']}">
    <div class="form-grid">
      <p><label>Full name</label><input name="full_name" value="{text_value(user.get('full_name'))}"></p>
      <p><label>Email</label><input name="email" type="email" value="{text_value(user.get('email'))}"></p>
      <p><label>Phone</label><input name="phone" value="{text_value(user.get('phone'))}"></p>
      <p><label>Country</label><input name="country" value="{text_value(user.get('country'))}"></p>
      <p><label>Status</label><select name="status">{status_options}</select></p>
    </div>
    <p><label>Admin notes</label><textarea name="admin_notes">{text_value(user.get('admin_notes'))}</textarea></p>
    <button type="submit">Save CRM Info</button>
  </form>
</section>
<section class="card">
  <h2>Deposits</h2>
  <table><thead><tr><th>ID</th><th>Crypto</th><th>Amount</th><th>Status</th><th>Created</th></tr></thead><tbody>{deposit_rows or empty_row(5)}</tbody></table>
</section>"""
    return html_response(body, title=f"User #{user_id}")


async def user_update_submit(request: web.Request) -> web.Response:
    require_admin(request)
    user_id = int(request.match_info["user_id"])
    form = await request.post()
    await db.update_user_crm_fields(
        user_id,
        {
            "full_name": str(form.get("full_name", "")),
            "email": str(form.get("email", "")),
            "phone": str(form.get("phone", "")),
            "country": str(form.get("country", "")),
            "status": str(form.get("status", "active")),
            "admin_notes": str(form.get("admin_notes", "")),
        },
    )
    redirect(f"/admin/users/{user_id}")


async def deposits_page(request: web.Request) -> web.Response:
    require_admin(request)
    status = request.query.get("status", "")
    status_filter = status if status in ("pending", "confirmed", "rejected") else None
    deposits = await db.list_deposits(status=status_filter, limit=100)
    rows = "".join(deposit_management_row(item) for item in deposits)
    body = f"""
<h1>Deposits</h1>
<section class="card actions">
  <a class="button{' button-secondary' if status_filter else ''}" href="/admin/deposits">All</a>
  <a class="button{' button-secondary' if status_filter != 'pending' else ''}" href="/admin/deposits?status=pending">Pending</a>
  <a class="button{' button-secondary' if status_filter != 'confirmed' else ''}" href="/admin/deposits?status=confirmed">Confirmed</a>
  <a class="button{' button-secondary' if status_filter != 'rejected' else ''}" href="/admin/deposits?status=rejected">Rejected</a>
</section>
<section class="card">
  <table><thead><tr><th>ID</th><th>User</th><th>Crypto</th><th>Amount</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead><tbody>{rows or empty_row(7)}</tbody></table>
</section>"""
    return html_response(body, title="CRM Deposits")


async def approve_deposit(request: web.Request) -> web.Response:
    require_admin(request)
    deposit_id = int(request.match_info["deposit_id"])
    form = await request.post()

    try:
        amount = float(form.get("amount", "0"))
    except ValueError:
        amount = 0

    deposit = await db.get_deposit(deposit_id)
    if deposit and deposit["status"] == "pending" and amount > 0:
        await db.update_deposit_status(deposit_id, "confirmed", amount)
        await db.update_balance(deposit["user_id"], amount)
        await notify_user(
            request,
            deposit["telegram_id"],
            f"Your deposit #{deposit_id} has been approved.\nAmount credited: ${amount:.2f}",
        )

    redirect("/admin/deposits?status=pending")


async def reject_deposit(request: web.Request) -> web.Response:
    require_admin(request)
    deposit_id = int(request.match_info["deposit_id"])
    deposit = await db.get_deposit(deposit_id)
    if deposit and deposit["status"] == "pending":
        await db.update_deposit_status(deposit_id, "rejected")
        await notify_user(
            request,
            deposit["telegram_id"],
            f"Your deposit #{deposit_id} has been rejected. Please contact support if this is an error.",
        )

    redirect("/admin/deposits?status=pending")


async def notify_user(request: web.Request, telegram_id: int, text: str):
    bot = request.app.get("bot")
    if not bot:
        return

    try:
        await bot.send_message(telegram_id, text)
    except Exception:
        pass


def user_row(user: dict) -> str:
    username = text_value(user.get("username")) or "N/A"
    full_name = text_value(user.get("full_name")) or "No name"
    contact = "<br>".join(
        item
        for item in (
            text_value(user.get("email")),
            text_value(user.get("phone")),
            text_value(user.get("country")),
        )
        if item
    )
    return f"""
<tr>
  <td><strong>{full_name}</strong><br><span class="muted">@{username} / {text_value(user.get('telegram_id'))}</span></td>
  <td>{contact or '<span class="muted">No contact info</span>'}</td>
  <td><span class="badge">{text_value(user.get('status') or 'active')}</span></td>
  <td>{format_money(user.get('balance'))}</td>
  <td><a class="button" href="/admin/users/{user['id']}">Open</a></td>
</tr>"""


def deposit_row(item: dict) -> str:
    return f"""
<tr>
  <td>#{item['id']}</td>
  <td>@{text_value(item.get('username')) or 'N/A'}</td>
  <td>{text_value(item.get('crypto'))}</td>
  <td>{format_money(item.get('amount')) if item.get('amount') else '<span class="muted">Not provided</span>'}</td>
  <td><span class="badge">{text_value(item.get('status'))}</span></td>
</tr>"""


def simple_deposit_row(item: dict) -> str:
    return f"""
<tr>
  <td>#{item['id']}</td>
  <td>{text_value(item.get('crypto'))}</td>
  <td>{format_money(item.get('amount')) if item.get('amount') else '<span class="muted">Not provided</span>'}</td>
  <td><span class="badge">{text_value(item.get('status'))}</span></td>
  <td>{text_value(item.get('created_at'))}</td>
</tr>"""


def deposit_management_row(item: dict) -> str:
    actions = '<span class="muted">No action</span>'
    amount_value = text_value(item.get("amount")) if item.get("amount") else ""
    if item.get("status") == "pending":
        actions = f"""
<div class="actions">
  <form method="post" action="/admin/deposits/{item['id']}/approve" class="actions">
    <input style="width: 120px;" name="amount" value="{amount_value}" placeholder="Amount">
    <button type="submit">Approve</button>
  </form>
  <form method="post" action="/admin/deposits/{item['id']}/reject">
    <button class="button-danger" type="submit">Reject</button>
  </form>
</div>"""

    return f"""
<tr>
  <td>#{item['id']}</td>
  <td><a href="/admin/users/{item['user_id']}">@{text_value(item.get('username')) or 'N/A'}</a><br><span class="muted">{text_value(item.get('telegram_id'))}</span></td>
  <td>{text_value(item.get('crypto'))}</td>
  <td>{format_money(item.get('amount')) if item.get('amount') else '<span class="muted">Not provided</span>'}</td>
  <td><span class="badge">{text_value(item.get('status'))}</span></td>
  <td>{text_value(item.get('created_at'))}</td>
  <td>{actions}</td>
</tr>"""


def empty_row(colspan: int) -> str:
    return f'<tr><td colspan="{colspan}" class="muted">No records found.</td></tr>'
