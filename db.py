import sqlite3
from typing import Any, List, Optional, Union
from config import DB_PATH

DDL_PRESENTS = """
CREATE TABLE IF NOT EXISTS presents (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    link TEXT,
    description TEXT,
    price INTEGER,
    currency TEXT,
    photo_url TEXT,
    is_booked INTEGER DEFAULT 0,
    giver_chat_id INTEGER,
    is_gifted INTEGER DEFAULT 0
);
"""

SEED_ITEMS = ["Apple", "Banana", "Carrot"]

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Ensure the presents table exists."""
    conn = get_conn()
    try:
        conn.execute(DDL_PRESENTS)
        conn.commit()
    finally:
        conn.close()

# -------- Create function (name + description + price + currency) --------

def create_present(
    name: str,
    description: str,
    price: int,
    currency: str,
) -> int:
    """
    Insert a new present row with the required fields for this operation.
    Returns the new row id.
    """
    name = (name or "").strip()
    currency = (currency or "").strip()

    if not name:
        raise ValueError("name is required")
    # description can be empty string; that's fine
    try:
        price_val = int(price)
    except Exception as e:
        raise ValueError("price must be an integer") from e

    conn = get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO presents (name, description, price, currency)
            VALUES (?, ?, ?, ?)
            """,
            (name, description, price_val, currency or None),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def get_present_by_id(present_id: int) -> Optional[dict]:
    """Return full present row as dict (or None if not found)."""
    conn = get_conn()
    try:
        row = conn.execute(
            """
            SELECT id, name, link, description, price, currency, photo_url,
                   is_booked, giver_chat_id, is_gifted
            FROM presents
            WHERE id = ?
            """,
            (present_id,),
        ).fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()

def list_presents() -> List[dict]:
    """Return [{id, name}] for all presents, ordered by id."""
    conn = get_conn()
    try:
        rows = conn.execute("SELECT id, name FROM presents ORDER BY id ASC").fetchall()
        return [{"id": r["id"], "name": r["name"]} for r in rows]
    finally:
        conn.close()

def list_booked_presents(giver_chat_id: int) -> List[dict]:
    """Return [{id, name}] for all presents, booked by user ordered by id."""
    conn = get_conn()
    try:
        rows = conn.execute(
                """
                SELECT id, name 
                    FROM presents 
                WHERE giver_chat_id = ? 
                ORDER BY id ASC
                """, 
                (giver_chat_id,),
            ).fetchall()
        return [{"id": r["id"], "name": r["name"]} for r in rows]
    finally:
        conn.close()

def try_book_present(present_id: int, giver_chat_id: int) -> dict:
    """
    Attempt to book the present (set is_booked=1, giver_chat_id=<chat id>)
    only if it is NOT already booked and NOT gifted.
    """
    conn = get_conn()
    try:
        # Try to book if free & not gifted
        cur = conn.execute(
            """
            UPDATE presents
               SET is_booked = 1,
                   giver_chat_id = ?
             WHERE id = ?
               AND IFNULL(is_booked, 0) = 0
               AND IFNULL(is_gifted, 0) = 0
            """,
            (giver_chat_id, present_id),
        )
        conn.commit()

        # Load the fresh row state
        row = conn.execute(
            """
            SELECT *
              FROM presents
             WHERE id = ?
            """,
            (present_id,),
        ).fetchone()

        if not row:
            return {"status": "not_found"}

        r = dict(row)

        return cur.rowcount == 1

    finally:
        conn.close()

def try_delete_present(present_id: int) -> dict:
    """
    Attempt to delete the present 
    """
    conn = get_conn()
    try:
        # Try to book if free & not gifted
        cur = conn.execute(
            """
            DELETE FROM presents
             WHERE id = ?
            """,
            (present_id,),
        )
        conn.commit()

        return cur.rowcount == 1

    finally:
        conn.close()


# -------- Internal helper for field updates --------

_ALLOWED_EDIT_FIELDS = {
    "link",
    "description",
    "price",
    "currency",
    "photo_url",
    "is_booked",
    "giver_chat_id",
    "is_gifted",
}

def _update_present_field(present_id: int, field: str, value: any) -> None:
    if field not in _ALLOWED_EDIT_FIELDS:
        raise ValueError(f"Field '{field}' is not editable or does not exist.")

    conn = get_conn()
    try:
        cur = conn.execute(
            f"UPDATE presents SET {field} = ? WHERE id = ?",
            (value, present_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"Present id {present_id} not found.")
    finally:
        conn.close()

# -------- Separate editing functions for each non-mandatory field --------

def set_present_link(present_id: int, link: Optional[str]) -> None:
    _update_present_field(present_id, "link", (link.strip() if link else None))

def set_present_description(present_id: int, description: Optional[str]) -> None:
    _update_present_field(present_id, "description", (description if description is not None else None))

def set_present_price(present_id: int, price: Optional[int]) -> None:
    if price is not None:
        try:
            price = int(price)
        except Exception as e:
            raise ValueError("price must be an integer or None") from e
    _update_present_field(present_id, "price", price)

def set_present_currency(present_id: int, currency: Optional[str]) -> None:
    _update_present_field(present_id, "currency", (currency.strip() if currency else None))

def set_present_photo_url(present_id: int, photo_url: Optional[str]) -> None:
    _update_present_field(present_id, "photo_url", (photo_url.strip() if photo_url else None))

def set_present_is_booked(present_id: int, is_booked: Optional[bool | int]) -> None:
    if is_booked is None:
        val = None
    else:
        val = 1 if bool(is_booked) else 0
    _update_present_field(present_id, "is_booked", val)

def set_present_giver_chat_id(present_id: int, giver_chat_id: Optional[int]) -> None:
    if giver_chat_id is not None:
        try:
            giver_chat_id = int(giver_chat_id)
        except Exception as e:
            raise ValueError("giver_chat_id must be an integer or None") from e
    _update_present_field(present_id, "giver_chat_id", giver_chat_id)

def set_present_is_gifted(present_id: int, is_gifted: Optional[bool | int]) -> None:
    if is_gifted is None:
        val = None
    else:
        val = 1 if bool(is_gifted) else 0
    _update_present_field(present_id, "is_gifted", val)