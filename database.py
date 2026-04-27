import aiosqlite

try:
    import asyncpg
except ModuleNotFoundError:
    asyncpg = None

from config import DATABASE_URL, DB_PATH


def use_postgres() -> bool:
    return bool(DATABASE_URL)


async def connect_postgres():
    if asyncpg is None:
        raise RuntimeError(
            "asyncpg is required when DATABASE_URL is set. Run: pip install -r requirements.txt"
        )

    # Supabase pooler works better with asyncpg's statement cache disabled.
    return await asyncpg.connect(DATABASE_URL, statement_cache_size=0)


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
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
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
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
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
