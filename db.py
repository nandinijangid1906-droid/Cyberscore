# -*- coding: utf-8 -*-
"""SQLite persistence layer for CyberScore."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "cyberscore.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS assessments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                taken_at    TEXT    NOT NULL,
                overall     REAL    NOT NULL,
                cat_scores  TEXT    NOT NULL,   -- JSON
                answers     TEXT    NOT NULL    -- JSON
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT    NOT NULL,
                description  TEXT    NOT NULL DEFAULT '',
                priority     TEXT    NOT NULL DEFAULT 'medium',
                category     TEXT    NOT NULL DEFAULT '',
                done         INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT    NOT NULL,
                done_at      TEXT
            );
        """)


# ── Assessment CRUD ────────────────────────────────────────────────────────

def save_assessment(overall: float, cat_scores: dict, answers: dict) -> int:
    """Persist an assessment; returns new row id."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO assessments (taken_at, overall, cat_scores, answers) VALUES (?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"),
             round(overall, 1),
             json.dumps(cat_scores),
             json.dumps(answers)),
        )
        return cur.lastrowid


def load_assessments() -> list[dict]:
    """Return all assessments newest-first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM assessments ORDER BY taken_at DESC, id DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["cat_scores"] = json.loads(d["cat_scores"])
        d["answers"]    = json.loads(d["answers"])
        result.append(d)
    return result


def delete_all_assessments() -> int:
    """Delete every assessment; returns count deleted."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM assessments")
        return cur.rowcount


# ── Task CRUD ──────────────────────────────────────────────────────────────

def load_tasks() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY done ASC, created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def add_task(title: str, description: str = "", priority: str = "medium",
             category: str = "") -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, description, priority, category, done, created_at) "
            "VALUES (?,?,?,?,0,?)",
            (title, description, priority, category,
             datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def toggle_task(task_id: int, done: bool) -> None:
    done_at = datetime.now().isoformat(timespec="seconds") if done else None
    with _connect() as conn:
        conn.execute(
            "UPDATE tasks SET done=?, done_at=? WHERE id=?",
            (1 if done else 0, done_at, task_id),
        )


def delete_task(task_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))


def delete_all_tasks() -> int:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM tasks")
        return cur.rowcount


def seed_tasks_from_recs(recommendations: list[dict]) -> None:
    """Insert recommendation actions as tasks (skip duplicates by title)."""
    existing = {t["title"] for t in load_tasks()}
    for rec in recommendations:
        if rec["title"] not in existing:
            add_task(
                title=rec["title"],
                description=rec["body"],
                priority=rec["priority"],
                category=rec.get("category", ""),
            )
