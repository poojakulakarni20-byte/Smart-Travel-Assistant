
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "travel_chat.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def initialize_database():
    with get_connection() as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            latency_ms INTEGER DEFAULT 0,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK (rating IN (-1, 1)),
            created_at TEXT NOT NULL,
            FOREIGN KEY (message_id) REFERENCES messages(message_id)
        );

        CREATE TABLE IF NOT EXISTS test_results (
            test_id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            expected TEXT NOT NULL,
            actual TEXT NOT NULL,
            correct INTEGER NOT NULL CHECK (correct IN (0, 1)),
            latency_ms INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """)


def create_session(session_id):
    with get_connection() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO sessions(session_id, created_at) VALUES (?, ?)",
            (session_id, now_utc())
        )


def save_message(
    session_id,
    role,
    content,
    latency_ms=0,
    input_tokens=0,
    output_tokens=0
):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO messages
            (session_id, role, content, latency_ms,
             input_tokens, output_tokens, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            role,
            content,
            int(latency_ms or 0),
            int(input_tokens or 0),
            int(output_tokens or 0),
            now_utc()
        ))
        return cursor.lastrowid


def get_session_messages(session_id, limit=100):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT message_id, role, content, latency_ms,
                   input_tokens, output_tokens, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY message_id DESC
            LIMIT ?
        """, (session_id, limit)).fetchall()

    return list(reversed([dict(row) for row in rows]))


def save_feedback(message_id, rating):
    if rating not in (-1, 1):
        raise ValueError("Rating must be -1 or 1.")

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO feedback(message_id, rating, created_at)
            VALUES (?, ?, ?)
        """, (message_id, rating, now_utc()))


def save_test_result(query, expected, actual, correct, latency_ms=0):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO test_results
            (query, expected, actual, correct, latency_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            query,
            expected,
            actual,
            1 if correct else 0,
            int(latency_ms or 0),
            now_utc()
        ))


def get_statistics():
    with get_connection() as connection:
        message_count = connection.execute(
            "SELECT COUNT(*) FROM messages"
        ).fetchone()[0]

        session_count = connection.execute(
            "SELECT COUNT(*) FROM sessions"
        ).fetchone()[0]

        feedback_count = connection.execute(
            "SELECT COUNT(*) FROM feedback"
        ).fetchone()[0]

        token_totals = connection.execute("""
            SELECT COALESCE(SUM(input_tokens), 0),
                   COALESCE(SUM(output_tokens), 0)
            FROM messages
        """).fetchone()

        average_latency = connection.execute("""
            SELECT AVG(latency_ms)
            FROM messages
            WHERE role = 'assistant' AND latency_ms > 0
        """).fetchone()[0]

    return {
        "messages": message_count,
        "sessions": session_count,
        "feedback": feedback_count,
        "input_tokens": token_totals[0],
        "output_tokens": token_totals[1],
        "average_latency_ms": average_latency or 0
    }
