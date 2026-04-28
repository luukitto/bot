import secrets

import aiosqlite

try:
    import asyncpg
except ModuleNotFoundError:
    asyncpg = None

from config import DATABASE_URL, DB_PATH

CRM_USER_COLUMNS = {
    "full_name": "TEXT",
    "email": "TEXT",
    "phone": "TEXT",
    "country": "TEXT",
    "status": "TEXT DEFAULT 'active'",
    "admin_notes": "TEXT",
    "updated_at": "TIMESTAMPTZ",
}


def use_postgres() -> bool:
    return bool(DATABASE_URL)


async def connect_postgres():
    if asyncpg is None:
        raise RuntimeError(
            "asyncpg is required when DATABASE_URL is set. Run: pip install -r requirements.txt"
        )

    # Supabase pooler works better with asyncpg's statement cache disabled.
    return await asyncpg.connect(DATABASE_URL, statement_cache_size=0)


async def ensure_postgres_crm_columns(conn):
    for column, column_type in CRM_USER_COLUMNS.items():
        await conn.execute(
            f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} {column_type}"
        )


async def ensure_sqlite_crm_columns(db):
    cursor = await db.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in await cursor.fetchall()}
    sqlite_columns = {
        **CRM_USER_COLUMNS,
        "updated_at": "TEXT",
    }

    for column, column_type in sqlite_columns.items():
        if column not in existing_columns:
            await db.execute(f"ALTER TABLE users ADD COLUMN {column} {column_type}")


async def init_db():
    if use_postgres():
        conn = await connect_postgres()
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    balance DOUBLE PRECISION DEFAULT 0.0,
                    full_name TEXT,
                    email TEXT,
                    phone TEXT,
                    country TEXT,
                    status TEXT DEFAULT 'active',
                    admin_notes TEXT,
                    updated_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            await ensure_postgres_crm_columns(conn)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS deposits (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    crypto TEXT NOT NULL,
                    amount DOUBLE PRECISION,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS signals_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    asset_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    signal_data TEXT,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS telegram_link_codes (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    code TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL,
                    used_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    actor_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_trading_accounts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    cash_balance DOUBLE PRECISION DEFAULT 100000,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMPTZ DEFAULT now(),
                    updated_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_orders (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity DOUBLE PRECISION NOT NULL,
                    order_type TEXT DEFAULT 'market',
                    estimated_price DOUBLE PRECISION,
                    status TEXT DEFAULT 'filled',
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlists (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    symbol TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    UNIQUE (user_id, symbol)
                )
            """)
        finally:
            await conn.close()
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                balance REAL DEFAULT 0.0,
                full_name TEXT,
                email TEXT,
                phone TEXT,
                country TEXT,
                status TEXT DEFAULT 'active',
                admin_notes TEXT,
                updated_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await ensure_sqlite_crm_columns(db)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                crypto TEXT NOT NULL,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS signals_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                asset_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal_data TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS telegram_link_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                code TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                actor_type TEXT NOT NULL,
                action TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS paper_trading_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                cash_balance REAL DEFAULT 100000,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS paper_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                order_type TEXT DEFAULT 'market',
                estimated_price REAL,
                status TEXT DEFAULT 'filled',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS watchlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE (user_id, symbol),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.commit()


async def get_user(telegram_id: int) -> dict | None:
    if use_postgres():
        conn = await connect_postgres()
        try:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1", telegram_id
            )
            return dict(row) if row else None
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_user(telegram_id: int, username: str | None) -> dict:
    if use_postgres():
        conn = await connect_postgres()
        try:
            await conn.execute(
                """INSERT INTO users (telegram_id, username)
                   VALUES ($1, $2)
                   ON CONFLICT (telegram_id)
                   DO UPDATE SET username = EXCLUDED.username""",
                telegram_id,
                username,
            )
        finally:
            await conn.close()
        return await get_user(telegram_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (telegram_id, username) VALUES (?, ?)",
            (telegram_id, username),
        )
        await db.commit()
    return await get_user(telegram_id)


async def log_user_activity(
    user_id: int | None,
    actor_type: str,
    action: str,
    metadata: str = "{}",
):
    if use_postgres():
        conn = await connect_postgres()
        try:
            await conn.execute(
                """
                INSERT INTO user_activity (user_id, actor_type, action, metadata)
                VALUES ($1, $2, $3, $4::jsonb)
                """,
                user_id,
                actor_type,
                action,
                metadata,
            )
        finally:
            await conn.close()
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_activity (user_id, actor_type, action, metadata)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, actor_type, action, metadata),
        )
        await db.commit()


async def create_telegram_link_code(user_id: int, ttl_seconds: int = 600) -> str:
    code = f"{secrets.randbelow(900000) + 100000}"

    if use_postgres():
        conn = await connect_postgres()
        try:
            await conn.execute(
                """
                UPDATE telegram_link_codes
                SET used_at = now()
                WHERE user_id = $1 AND used_at IS NULL
                """,
                user_id,
            )
            await conn.execute(
                """
                INSERT INTO telegram_link_codes (user_id, code, expires_at)
                VALUES ($1, $2, now() + ($3 * interval '1 second'))
                """,
                user_id,
                code,
                ttl_seconds,
            )
        finally:
            await conn.close()
        await log_user_activity(user_id, "bot", "website_link_code_created")
        return code

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE telegram_link_codes
            SET used_at = datetime('now')
            WHERE user_id = ? AND used_at IS NULL
            """,
            (user_id,),
        )
        await db.execute(
            """
            INSERT INTO telegram_link_codes (user_id, code, expires_at)
            VALUES (?, ?, datetime('now', '+' || ? || ' seconds'))
            """,
            (user_id, code, ttl_seconds),
        )
        await db.commit()
    await log_user_activity(user_id, "bot", "website_link_code_created")
    return code


async def get_balance(telegram_id: int) -> float:
    user = await get_user(telegram_id)
    return user["balance"] if user else 0.0


async def update_balance(user_id: int, amount: float):
    if use_postgres():
        conn = await connect_postgres()
        try:
            await conn.execute(
                "UPDATE users SET balance = balance + $1 WHERE id = $2",
                amount,
                user_id,
            )
        finally:
            await conn.close()
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?",
            (amount, user_id),
        )
        await db.commit()


async def create_deposit(user_id: int, crypto: str, amount: float | None = None) -> int:
    if use_postgres():
        conn = await connect_postgres()
        try:
            return await conn.fetchval(
                "INSERT INTO deposits (user_id, crypto, amount) VALUES ($1, $2, $3) RETURNING id",
                user_id,
                crypto,
                amount,
            )
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO deposits (user_id, crypto, amount) VALUES (?, ?, ?)",
            (user_id, crypto, amount),
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_deposits() -> list[dict]:
    if use_postgres():
        conn = await connect_postgres()
        try:
            rows = await conn.fetch(
                """SELECT d.*, u.telegram_id, u.username
                   FROM deposits d JOIN users u ON d.user_id = u.id
                   WHERE d.status = 'pending'
                   ORDER BY d.created_at DESC"""
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT d.*, u.telegram_id, u.username
               FROM deposits d JOIN users u ON d.user_id = u.id
               WHERE d.status = 'pending'
               ORDER BY d.created_at DESC"""
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_deposit(deposit_id: int) -> dict | None:
    if use_postgres():
        conn = await connect_postgres()
        try:
            row = await conn.fetchrow(
                """SELECT d.*, u.telegram_id, u.username
                   FROM deposits d JOIN users u ON d.user_id = u.id
                   WHERE d.id = $1""",
                deposit_id,
            )
            return dict(row) if row else None
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT d.*, u.telegram_id, u.username
               FROM deposits d JOIN users u ON d.user_id = u.id
               WHERE d.id = ?""",
            (deposit_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_deposit_status(deposit_id: int, status: str, amount: float = None):
    if use_postgres():
        conn = await connect_postgres()
        try:
            if amount is not None:
                await conn.execute(
                    "UPDATE deposits SET status = $1, amount = $2 WHERE id = $3",
                    status,
                    amount,
                    deposit_id,
                )
            else:
                await conn.execute(
                    "UPDATE deposits SET status = $1 WHERE id = $2",
                    status,
                    deposit_id,
                )
        finally:
            await conn.close()
        return

    async with aiosqlite.connect(DB_PATH) as db:
        if amount is not None:
            await db.execute(
                "UPDATE deposits SET status = ?, amount = ? WHERE id = ?",
                (status, amount, deposit_id),
            )
        else:
            await db.execute(
                "UPDATE deposits SET status = ? WHERE id = ?",
                (status, deposit_id),
            )
        await db.commit()


async def get_user_deposits(telegram_id: int, limit: int = 5) -> list[dict]:
    if use_postgres():
        conn = await connect_postgres()
        try:
            rows = await conn.fetch(
                """SELECT d.* FROM deposits d
                   JOIN users u ON d.user_id = u.id
                   WHERE u.telegram_id = $1
                   ORDER BY d.created_at DESC LIMIT $2""",
                telegram_id,
                limit,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT d.* FROM deposits d
               JOIN users u ON d.user_id = u.id
               WHERE u.telegram_id = ?
               ORDER BY d.created_at DESC LIMIT ?""",
            (telegram_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def save_signal(user_id: int, asset_type: str, symbol: str, signal_data: str):
    if use_postgres():
        conn = await connect_postgres()
        try:
            await conn.execute(
                "INSERT INTO signals_history (user_id, asset_type, symbol, signal_data) VALUES ($1, $2, $3, $4)",
                user_id,
                asset_type,
                symbol,
                signal_data,
            )
        finally:
            await conn.close()
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO signals_history (user_id, asset_type, symbol, signal_data) VALUES (?, ?, ?, ?)",
            (user_id, asset_type, symbol, signal_data),
        )
        await db.commit()


async def list_users(limit: int = 20) -> list[dict]:
    if use_postgres():
        conn = await connect_postgres()
        try:
            rows = await conn.fetch(
                """SELECT id, telegram_id, username, balance, created_at
                   FROM users
                   ORDER BY created_at DESC
                   LIMIT $1""",
                limit,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT id, telegram_id, username, balance, created_at
               FROM users
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_dashboard_stats() -> dict:
    if use_postgres():
        conn = await connect_postgres()
        try:
            row = await conn.fetchrow(
                """
                SELECT
                    (SELECT COUNT(*) FROM users) AS total_users,
                    (SELECT COUNT(*) FROM deposits WHERE status = 'pending') AS pending_deposits,
                    (SELECT COALESCE(SUM(balance), 0) FROM users) AS total_balance
                """
            )
            return dict(row)
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM users) AS total_users,
                (SELECT COUNT(*) FROM deposits WHERE status = 'pending') AS pending_deposits,
                (SELECT COALESCE(SUM(balance), 0) FROM users) AS total_balance
            """
        )
        row = await cursor.fetchone()
        return dict(row)


async def list_crm_users(
    search: str | None = None, limit: int = 50, offset: int = 0
) -> list[dict]:
    search = (search or "").strip()

    if use_postgres():
        conn = await connect_postgres()
        try:
            if search:
                rows = await conn.fetch(
                    """
                    SELECT id, telegram_id, username, balance, full_name, email, phone,
                           country, status, created_at, updated_at
                    FROM users
                    WHERE CAST(telegram_id AS TEXT) ILIKE $1
                       OR COALESCE(username, '') ILIKE $1
                       OR COALESCE(full_name, '') ILIKE $1
                       OR COALESCE(email, '') ILIKE $1
                       OR COALESCE(phone, '') ILIKE $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    f"%{search}%",
                    limit,
                    offset,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, telegram_id, username, balance, full_name, email, phone,
                           country, status, created_at, updated_at
                    FROM users
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if search:
            cursor = await db.execute(
                """
                SELECT id, telegram_id, username, balance, full_name, email, phone,
                       country, status, created_at, updated_at
                FROM users
                WHERE CAST(telegram_id AS TEXT) LIKE ?
                   OR COALESCE(username, '') LIKE ?
                   OR COALESCE(full_name, '') LIKE ?
                   OR COALESCE(email, '') LIKE ?
                   OR COALESCE(phone, '') LIKE ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (f"%{search}%",) * 5 + (limit, offset),
            )
        else:
            cursor = await db.execute(
                """
                SELECT id, telegram_id, username, balance, full_name, email, phone,
                       country, status, created_at, updated_at
                FROM users
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_user_by_id(user_id: int) -> dict | None:
    if use_postgres():
        conn = await connect_postgres()
        try:
            row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            return dict(row) if row else None
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_user_crm_fields(user_id: int, fields: dict):
    allowed_fields = {
        "full_name",
        "email",
        "phone",
        "country",
        "status",
        "admin_notes",
    }
    clean_fields = {
        key: (value.strip() if isinstance(value, str) else value)
        for key, value in fields.items()
        if key in allowed_fields
    }

    if not clean_fields:
        return

    if use_postgres():
        conn = await connect_postgres()
        try:
            assignments = []
            values = []
            for index, (key, value) in enumerate(clean_fields.items(), start=1):
                assignments.append(f"{key} = ${index}")
                values.append(value or None)
            values.append(user_id)
            await conn.execute(
                f"""
                UPDATE users
                SET {', '.join(assignments)}, updated_at = now()
                WHERE id = ${len(values)}
                """,
                *values,
            )
        finally:
            await conn.close()
        return

    async with aiosqlite.connect(DB_PATH) as db:
        assignments = [f"{key} = ?" for key in clean_fields]
        values = [value or None for value in clean_fields.values()]
        values.append(user_id)
        await db.execute(
            f"""
            UPDATE users
            SET {', '.join(assignments)}, updated_at = datetime('now')
            WHERE id = ?
            """,
            values,
        )
        await db.commit()


async def get_user_deposits_by_id(user_id: int, limit: int = 20) -> list[dict]:
    if use_postgres():
        conn = await connect_postgres()
        try:
            rows = await conn.fetch(
                """
                SELECT * FROM deposits
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM deposits
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def list_deposits(status: str | None = None, limit: int = 50) -> list[dict]:
    if use_postgres():
        conn = await connect_postgres()
        try:
            if status:
                rows = await conn.fetch(
                    """
                    SELECT d.*, u.telegram_id, u.username, u.full_name, u.email
                    FROM deposits d
                    JOIN users u ON d.user_id = u.id
                    WHERE d.status = $1
                    ORDER BY d.created_at DESC
                    LIMIT $2
                    """,
                    status,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT d.*, u.telegram_id, u.username, u.full_name, u.email
                    FROM deposits d
                    JOIN users u ON d.user_id = u.id
                    ORDER BY d.created_at DESC
                    LIMIT $1
                    """,
                    limit,
                )
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute(
                """
                SELECT d.*, u.telegram_id, u.username, u.full_name, u.email
                FROM deposits d
                JOIN users u ON d.user_id = u.id
                WHERE d.status = ?
                ORDER BY d.created_at DESC
                LIMIT ?
                """,
                (status, limit),
            )
        else:
            cursor = await db.execute(
                """
                SELECT d.*, u.telegram_id, u.username, u.full_name, u.email
                FROM deposits d
                JOIN users u ON d.user_id = u.id
                ORDER BY d.created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
