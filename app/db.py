from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from app.models import Lead, LeadActivity, LeadActivityCreate, LeadCreate, LeadUpdate


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "data"
DATABASE_PATH = DATABASE_DIR / "leadbot.db"


def init_db() -> None:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                website TEXT,
                address TEXT,
                category TEXT,
                source TEXT,
                status TEXT,
                note TEXT,
                next_contact_date TEXT,
                query_label TEXT,
                email_delivery_status TEXT,
                email_last_event_at TEXT,
                email_replied_at TEXT,
                email_bounced_at TEXT,
                email_unsubscribed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scrape_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_label TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lead_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                activity_note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_column(connection, "note", "TEXT")
        _ensure_column(connection, "next_contact_date", "TEXT")
        _ensure_column(connection, "query_label", "TEXT")
        _ensure_column(connection, "email_delivery_status", "TEXT")
        _ensure_column(connection, "email_last_event_at", "TEXT")
        _ensure_column(connection, "email_replied_at", "TEXT")
        _ensure_column(connection, "email_bounced_at", "TEXT")
        _ensure_column(connection, "email_unsubscribed_at", "TEXT")
        connection.commit()


def _ensure_column(connection: sqlite3.Connection, column_name: str, column_type: str) -> None:
    existing_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(leads)").fetchall()
    }
    if column_name not in existing_columns:
        connection.execute(f"ALTER TABLE leads ADD COLUMN {column_name} {column_type}")


@contextmanager
def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def get_all_leads(
    search: str | None = None,
    category: str | None = None,
    status: str | None = None,
    next_contact_date: str | None = None,
    query_labels: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Lead]:
    where_clause, values = _build_lead_filters(
        search=search,
        category=category,
        status=status,
        next_contact_date=next_contact_date,
        query_labels=query_labels,
    )

    query = f"""
        SELECT
            id,
            business_name,
            phone,
            email,
            website,
            address,
            category,
            source,
            status,
            note,
            next_contact_date,
            query_label,
            email_delivery_status,
            email_last_event_at,
            email_replied_at,
            email_bounced_at,
            email_unsubscribed_at,
            created_at
        FROM leads
        {where_clause}
        ORDER BY id DESC
    """
    query_values = list(values)

    if limit is not None:
        query += "\nLIMIT ? OFFSET ?"
        query_values.extend([limit, offset])

    with get_connection() as connection:
        rows = connection.execute(query, query_values).fetchall()

    return [Lead(**dict(row)) for row in rows]


def count_all_leads(
    search: str | None = None,
    category: str | None = None,
    status: str | None = None,
    next_contact_date: str | None = None,
    query_labels: list[str] | None = None,
) -> int:
    where_clause, values = _build_lead_filters(
        search=search,
        category=category,
        status=status,
        next_contact_date=next_contact_date,
        query_labels=query_labels,
    )

    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM leads
            {where_clause}
            """,
            values,
        ).fetchone()

    return int(row["total"]) if row else 0


def _build_lead_filters(
    search: str | None = None,
    category: str | None = None,
    status: str | None = None,
    next_contact_date: str | None = None,
    query_labels: list[str] | None = None,
) -> tuple[str, list[str]]:
    conditions: list[str] = []
    values: list[str] = []

    if search:
        conditions.append(
            """
            (
                lower(business_name) LIKE ?
                OR lower(phone) LIKE ?
                OR lower(email) LIKE ?
                OR lower(website) LIKE ?
                OR lower(address) LIKE ?
                OR lower(category) LIKE ?
                OR lower(note) LIKE ?
                OR lower(query_label) LIKE ?
            )
            """
        )
        search_value = f"%{search.casefold()}%"
        values.extend([search_value] * 8)

    if category:
        conditions.append("lower(category) LIKE ?")
        values.append(f"%{category.casefold()}%")

    if status:
        conditions.append("lower(status) LIKE ?")
        values.append(f"%{status.casefold()}%")

    if next_contact_date:
        conditions.append("lower(next_contact_date) LIKE ?")
        values.append(f"%{next_contact_date.casefold()}%")

    normalized_query_labels = [
        label.casefold().strip()
        for label in (query_labels or [])
        if label and label.strip()
    ]
    if normalized_query_labels:
        placeholders = ", ".join("?" for _ in normalized_query_labels)
        conditions.append(f"lower(query_label) IN ({placeholders})")
        values.extend(normalized_query_labels)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_clause, values


def get_query_labels() -> list[str]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT query_label
            FROM scrape_queries
            WHERE query_label IS NOT NULL AND trim(query_label) != ''
            GROUP BY query_label
            ORDER BY MAX(id) DESC
            """
        ).fetchall()

    return [row["query_label"] for row in rows]


def save_scrape_query(query_label: str) -> None:
    cleaned = " ".join(query_label.split()).strip()
    if not cleaned:
        return

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO scrape_queries (query_label)
            VALUES (?)
            """,
            (cleaned,),
        )
        connection.commit()


def get_follow_up_summary(limit_per_group: int = 8) -> tuple[list[Lead], list[Lead]]:
    today_value = date.today().isoformat()

    with get_connection() as connection:
        today_rows = connection.execute(
            """
            SELECT
                id,
                business_name,
                phone,
                email,
                website,
                address,
                category,
                source,
                status,
                note,
                next_contact_date,
                query_label,
                email_delivery_status,
                email_last_event_at,
                email_replied_at,
                email_bounced_at,
                email_unsubscribed_at,
                created_at
            FROM leads
            WHERE next_contact_date = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (today_value, limit_per_group),
        ).fetchall()

        overdue_rows = connection.execute(
            """
            SELECT
                id,
                business_name,
                phone,
                email,
                website,
                address,
                category,
                source,
                status,
                note,
                next_contact_date,
                query_label,
                email_delivery_status,
                email_last_event_at,
                email_replied_at,
                email_bounced_at,
                email_unsubscribed_at,
                created_at
            FROM leads
            WHERE next_contact_date IS NOT NULL
              AND trim(next_contact_date) != ''
              AND next_contact_date < ?
              AND lower(COALESCE(status, '')) NOT IN ('won', 'lost')
            ORDER BY next_contact_date ASC, id DESC
            LIMIT ?
            """,
            (today_value, limit_per_group),
        ).fetchall()

    return (
        [Lead(**dict(row)) for row in today_rows],
        [Lead(**dict(row)) for row in overdue_rows],
    )


def get_lead_activities(lead_id: int, limit: int = 20) -> list[LeadActivity]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                lead_id,
                activity_type,
                activity_note,
                created_at
            FROM lead_activities
            WHERE lead_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (lead_id, limit),
        ).fetchall()

    return [LeadActivity(**dict(row)) for row in rows]


def create_lead_activity(lead_id: int, payload: LeadActivityCreate) -> LeadActivity | None:
    with get_connection() as connection:
        lead_row = connection.execute(
            "SELECT id FROM leads WHERE id = ?",
            (lead_id,),
        ).fetchone()
        if lead_row is None:
            return None

        cursor = connection.execute(
            """
            INSERT INTO lead_activities (
                lead_id,
                activity_type,
                activity_note
            )
            VALUES (?, ?, ?)
            """,
            (lead_id, payload.activity_type, payload.activity_note),
        )
        _apply_activity_side_effects(connection, [lead_id], payload.activity_type)
        connection.commit()

        row = connection.execute(
            """
            SELECT
                id,
                lead_id,
                activity_type,
                activity_note,
                created_at
            FROM lead_activities
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return LeadActivity(**dict(row))


def create_activities_for_leads(
    lead_ids: list[int],
    activity_type: str,
    activity_note: str | None = None,
) -> int:
    if not lead_ids:
        return 0

    rows = [(lead_id, activity_type, activity_note) for lead_id in lead_ids]
    with get_connection() as connection:
        connection.executemany(
            """
            INSERT INTO lead_activities (
                lead_id,
                activity_type,
                activity_note
            )
            VALUES (?, ?, ?)
            """,
            rows,
        )
        _apply_activity_side_effects(connection, lead_ids, activity_type)
        connection.commit()

    return len(rows)


def get_leads_by_ids(ids: list[int]) -> list[Lead]:
    if not ids:
        return []

    placeholders = ", ".join("?" for _ in ids)
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                id,
                business_name,
                phone,
                email,
                website,
                address,
                category,
                source,
                status,
                note,
                next_contact_date,
                query_label,
                email_delivery_status,
                email_last_event_at,
                email_replied_at,
                email_bounced_at,
                email_unsubscribed_at,
                created_at
            FROM leads
            WHERE id IN ({placeholders})
            ORDER BY id DESC
            """,
            ids,
        ).fetchall()

    return [Lead(**dict(row)) for row in rows]


def clear_all_leads() -> int:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM leads")
        connection.commit()

    return cursor.rowcount


def delete_lead(lead_id: int) -> int:
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM lead_activities
            WHERE lead_id = ?
            """,
            (lead_id,),
        )
        cursor = connection.execute(
            """
            DELETE FROM leads
            WHERE id = ?
            """,
            (lead_id,),
        )
        connection.commit()

    return cursor.rowcount


def bulk_update_lead_status(lead_ids: list[int], status: str) -> int:
    if not lead_ids:
        return 0

    placeholders = ", ".join("?" for _ in lead_ids)
    with get_connection() as connection:
        cursor = connection.execute(
            f"""
            UPDATE leads
            SET status = ?
            WHERE id IN ({placeholders})
            """,
            [status, *lead_ids],
        )
        connection.commit()

    return cursor.rowcount


def bulk_set_next_contact_date(lead_ids: list[int], next_contact_date: str) -> int:
    if not lead_ids:
        return 0

    placeholders = ", ".join("?" for _ in lead_ids)
    with get_connection() as connection:
        cursor = connection.execute(
            f"""
            UPDATE leads
            SET next_contact_date = ?
            WHERE id IN ({placeholders})
            """,
            [next_contact_date, *lead_ids],
        )
        connection.commit()

    return cursor.rowcount


def mark_lead_contacted(lead_id: int) -> Lead | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                business_name,
                phone,
                email,
                website,
                address,
                category,
                source,
                status,
                note,
                next_contact_date,
                query_label,
                email_delivery_status,
                email_last_event_at,
                email_replied_at,
                email_bounced_at,
                email_unsubscribed_at,
                created_at
            FROM leads
            WHERE id = ?
            """,
            (lead_id,),
        ).fetchone()

        if row is None:
            return None

        current_status = (row["status"] or "").strip().casefold()
        if current_status in {"", "new"}:
            connection.execute(
                """
                UPDATE leads
                SET status = 'contacted'
                WHERE id = ?
                """,
                (lead_id,),
            )
            connection.commit()

            row = connection.execute(
                """
                SELECT
                    id,
                    business_name,
                    phone,
                    email,
                    website,
                    address,
                    category,
                    source,
                    status,
                    note,
                    next_contact_date,
                    query_label,
                    email_delivery_status,
                    email_last_event_at,
                    email_replied_at,
                    email_bounced_at,
                    email_unsubscribed_at,
                    created_at
                FROM leads
                WHERE id = ?
                """,
                (lead_id,),
            ).fetchone()

    return Lead(**dict(row))


def insert_lead(payload: LeadCreate) -> Lead:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO leads (
                business_name,
                phone,
                email,
                website,
                address,
                category,
                source,
                status,
                note,
                next_contact_date,
                query_label,
                email_delivery_status,
                email_last_event_at,
                email_replied_at,
                email_bounced_at,
                email_unsubscribed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _lead_values(payload),
        )
        connection.commit()

        row = connection.execute(
            """
            SELECT
                id,
                business_name,
                phone,
                email,
                website,
                address,
                category,
                source,
                status,
                note,
                next_contact_date,
                query_label,
                email_delivery_status,
                email_last_event_at,
                email_replied_at,
                email_bounced_at,
                email_unsubscribed_at,
                created_at
            FROM leads
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return Lead(**dict(row))


def update_lead(lead_id: int, payload: LeadUpdate) -> Lead | None:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE leads
            SET
                business_name = ?,
                phone = ?,
                email = ?,
                website = ?,
                address = ?,
                category = ?,
                source = ?,
                status = ?,
                note = ?,
                next_contact_date = ?,
                query_label = ?,
                email_delivery_status = ?,
                email_last_event_at = ?,
                email_replied_at = ?,
                email_bounced_at = ?,
                email_unsubscribed_at = ?
            WHERE id = ?
            """,
            (*_lead_values(payload), lead_id),
        )
        connection.commit()

        if cursor.rowcount == 0:
            return None

        row = connection.execute(
            """
            SELECT
                id,
                business_name,
                phone,
                email,
                website,
                address,
                category,
                source,
                status,
                note,
                next_contact_date,
                query_label,
                email_delivery_status,
                email_last_event_at,
                email_replied_at,
                email_bounced_at,
                email_unsubscribed_at,
                created_at
            FROM leads
            WHERE id = ?
            """,
            (lead_id,),
        ).fetchone()

    return Lead(**dict(row))


def insert_lead_if_new(payload: LeadCreate) -> bool:
    if not payload.business_name.strip():
        return False

    with get_connection() as connection:
        if lead_exists(connection, payload):
            return False

        connection.execute(
            """
            INSERT INTO leads (
                business_name,
                phone,
                email,
                website,
                address,
                category,
                source,
                status,
                note,
                next_contact_date,
                query_label,
                email_delivery_status,
                email_last_event_at,
                email_replied_at,
                email_bounced_at,
                email_unsubscribed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _lead_values(payload),
        )
        connection.commit()

    return True


def _lead_values(
    payload: LeadCreate | LeadUpdate,
) -> tuple[
    str,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
]:
    return (
        payload.business_name,
        payload.phone,
        payload.email,
        payload.website,
        payload.address,
        payload.category,
        payload.source,
        payload.status,
        payload.note,
        payload.next_contact_date,
        payload.query_label,
        payload.email_delivery_status,
        payload.email_last_event_at,
        payload.email_replied_at,
        payload.email_bounced_at,
        payload.email_unsubscribed_at,
    )


def _normalize_for_match(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = " ".join(value.split()).strip()
    return cleaned.casefold() if cleaned else None


def lead_exists(connection: sqlite3.Connection, payload: LeadCreate | LeadUpdate) -> bool:
    business_name_key = _normalize_for_match(payload.business_name)
    phone_key = _normalize_for_match(payload.phone)
    address_key = _normalize_for_match(payload.address)
    website_key = _normalize_for_match(payload.website)

    if not business_name_key:
        return True

    rows = connection.execute(
        """
        SELECT business_name, phone, address, website
        FROM leads
        WHERE lower(trim(business_name)) = ?
        """,
        (business_name_key,),
    ).fetchall()

    for row in rows:
        row_phone = _normalize_for_match(row["phone"])
        row_address = _normalize_for_match(row["address"])
        row_website = _normalize_for_match(row["website"])

        if phone_key and row_phone and phone_key == row_phone:
            return True

        if address_key and row_address and address_key == row_address:
            return True

        if website_key and row_website and website_key == row_website:
            return True

    return False


def insert_leads_if_new(leads: Iterable[LeadCreate]) -> tuple[int, int]:
    saved_count = 0
    skipped_count = 0

    with get_connection() as connection:
        for lead in leads:
            if not lead.business_name.strip():
                skipped_count += 1
                continue

            if lead_exists(connection, lead):
                skipped_count += 1
                continue

            connection.execute(
                """
                INSERT INTO leads (
                    business_name,
                    phone,
                    email,
                    website,
                    address,
                    category,
                    source,
                    status,
                    note,
                    next_contact_date,
                    query_label,
                    email_delivery_status,
                    email_last_event_at,
                    email_replied_at,
                    email_bounced_at,
                    email_unsubscribed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _lead_values(lead),
            )
            saved_count += 1

        connection.commit()

    return saved_count, skipped_count


def _apply_activity_side_effects(
    connection: sqlite3.Connection,
    lead_ids: list[int],
    activity_type: str,
) -> None:
    if not lead_ids:
        return

    normalized = (activity_type or "").strip().casefold()
    if not normalized:
        return

    event_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    placeholders = ", ".join("?" for _ in lead_ids)

    if normalized == "email_prepared":
        connection.execute(
            f"""
            UPDATE leads
            SET
                email_delivery_status = 'prepared',
                email_last_event_at = ?
            WHERE id IN ({placeholders})
            """,
            [event_time, *lead_ids],
        )
        return

    if normalized == "email_opened":
        connection.execute(
            f"""
            UPDATE leads
            SET
                email_delivery_status = 'opened',
                email_last_event_at = ?
            WHERE id IN ({placeholders})
            """,
            [event_time, *lead_ids],
        )
        return

    if normalized == "email_replied":
        connection.execute(
            f"""
            UPDATE leads
            SET
                email_delivery_status = 'replied',
                email_last_event_at = ?,
                email_replied_at = COALESCE(email_replied_at, ?)
            WHERE id IN ({placeholders})
            """,
            [event_time, event_time, *lead_ids],
        )
        return

    if normalized == "email_bounced":
        connection.execute(
            f"""
            UPDATE leads
            SET
                email_delivery_status = 'bounced',
                email_last_event_at = ?,
                email_bounced_at = COALESCE(email_bounced_at, ?)
            WHERE id IN ({placeholders})
            """,
            [event_time, event_time, *lead_ids],
        )
        return

    if normalized == "email_unsubscribed":
        connection.execute(
            f"""
            UPDATE leads
            SET
                email_delivery_status = 'unsubscribed',
                email_last_event_at = ?,
                email_unsubscribed_at = COALESCE(email_unsubscribed_at, ?)
            WHERE id IN ({placeholders})
            """,
            [event_time, event_time, *lead_ids],
        )
