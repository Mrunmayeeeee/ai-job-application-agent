"""
SQLite database models for tracking job applications.
Handles storage, retrieval, and analytics for all scraped jobs and applications.
"""

import sqlite3
import json
from datetime import datetime
from config import Config


class Database:
    """SQLite-backed application tracking database."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DB_PATH
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT DEFAULT '',
                description TEXT DEFAULT '',
                requirements TEXT DEFAULT '',
                salary TEXT DEFAULT '',
                job_url TEXT UNIQUE,
                source TEXT DEFAULT '',
                job_type TEXT DEFAULT '',
                experience_level TEXT DEFAULT '',
                posted_date TEXT DEFAULT '',
                scraped_at TEXT NOT NULL,
                skills_required TEXT DEFAULT '[]',
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                status TEXT DEFAULT 'matched',
                match_score REAL DEFAULT 0.0,
                match_reasons TEXT DEFAULT '',
                cover_letter TEXT DEFAULT '',
                cover_letter_path TEXT DEFAULT '',
                applied_at TEXT,
                notes TEXT DEFAULT '',
                decision_reasoning TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            );

            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                skills TEXT DEFAULT '[]',
                uploaded_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
            CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
            CREATE INDEX IF NOT EXISTS idx_applications_score ON applications(match_score);
        """)
        conn.commit()
        conn.close()

    # ── Jobs ─────────────────────────────────────────────────────────

    def add_job(self, job_data: dict) -> int:
        """Insert a new job listing. Returns the job ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO jobs 
                (title, company, location, description, requirements, salary,
                 job_url, source, job_type, experience_level, posted_date,
                 scraped_at, skills_required)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_data.get("title", ""),
                job_data.get("company", ""),
                job_data.get("location", ""),
                job_data.get("description", ""),
                job_data.get("requirements", ""),
                job_data.get("salary", ""),
                job_data.get("job_url", ""),
                job_data.get("source", ""),
                job_data.get("job_type", ""),
                job_data.get("experience_level", ""),
                job_data.get("posted_date", ""),
                datetime.now().isoformat(),
                json.dumps(job_data.get("skills_required", [])),
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def add_jobs_bulk(self, jobs: list[dict]) -> int:
        """Insert multiple jobs. Returns count of newly inserted jobs."""
        count = 0
        for job in jobs:
            job_id = self.add_job(job)
            if job_id:
                count += 1
        return count

    def get_jobs(self, source: str = None, limit: int = 100,
                 offset: int = 0, active_only: bool = True) -> list[dict]:
        """Retrieve jobs with optional filtering."""
        conn = self._get_conn()
        query = "SELECT * FROM jobs WHERE 1=1"
        params = []

        if active_only:
            query += " AND is_active = 1"
        if source:
            query += " AND source = ?"
            params.append(source)

        query += " ORDER BY scraped_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_job_by_id(self, job_id: int) -> dict | None:
        """Get a single job by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_unprocessed_jobs(self) -> list[dict]:
        """Get jobs that haven't been matched/processed yet."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT j.* FROM jobs j
            LEFT JOIN applications a ON j.id = a.job_id
            WHERE a.id IS NULL AND j.is_active = 1
            ORDER BY j.scraped_at DESC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_job_count(self, source: str = None) -> int:
        """Get total count of jobs, optionally by source."""
        conn = self._get_conn()
        if source:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM jobs WHERE source = ?", (source,)
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) as cnt FROM jobs").fetchone()
        conn.close()
        return row["cnt"]

    # ── Applications ─────────────────────────────────────────────────

    def add_application(self, app_data: dict) -> int:
        """Create an application entry for a matched job."""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        try:
            cursor = conn.execute("""
                INSERT INTO applications
                (job_id, status, match_score, match_reasons, cover_letter,
                 cover_letter_path, decision_reasoning, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                app_data["job_id"],
                app_data.get("status", "matched"),
                app_data.get("match_score", 0.0),
                app_data.get("match_reasons", ""),
                app_data.get("cover_letter", ""),
                app_data.get("cover_letter_path", ""),
                app_data.get("decision_reasoning", ""),
                app_data.get("notes", ""),
                now, now,
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_application(self, app_id: int, updates: dict):
        """Update an application's fields."""
        conn = self._get_conn()
        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [app_id]
        conn.execute(
            f"UPDATE applications SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
        conn.close()

    def get_applications(self, status: str = None, min_score: float = None,
                         limit: int = 100) -> list[dict]:
        """Retrieve applications with optional filtering."""
        conn = self._get_conn()
        query = """
            SELECT a.*, j.title, j.company, j.location, j.job_url, j.source
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND a.status = ?"
            params.append(status)
        if min_score is not None:
            query += " AND a.match_score >= ?"
            params.append(min_score)

        query += " ORDER BY a.match_score DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_application_by_id(self, app_id: int) -> dict | None:
        """Get a single application with job details."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT a.*, j.title, j.company, j.location, j.description,
                   j.requirements, j.job_url, j.source
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE a.id = ?
        """, (app_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    # ── Resumes ──────────────────────────────────────────────────────

    def save_resume(self, file_name: str, file_path: str,
                    raw_text: str, skills: list[str]) -> int:
        """Save a parsed resume to the database."""
        conn = self._get_conn()
        # Deactivate old resumes
        conn.execute("UPDATE resumes SET is_active = 0")
        cursor = conn.execute("""
            INSERT INTO resumes (file_name, file_path, raw_text, skills, uploaded_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (file_name, file_path, raw_text, json.dumps(skills),
              datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return cursor.lastrowid

    def get_active_resume(self) -> dict | None:
        """Get the currently active resume."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM resumes WHERE is_active = 1 ORDER BY uploaded_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            result = dict(row)
            result["skills"] = json.loads(result["skills"])
            return result
        return None

    # ── Analytics ────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get dashboard statistics."""
        conn = self._get_conn()
        stats = {}

        stats["total_jobs"] = conn.execute(
            "SELECT COUNT(*) as cnt FROM jobs"
        ).fetchone()["cnt"]

        stats["total_applications"] = conn.execute(
            "SELECT COUNT(*) as cnt FROM applications"
        ).fetchone()["cnt"]

        stats["avg_match_score"] = conn.execute(
            "SELECT COALESCE(AVG(match_score), 0) as avg FROM applications"
        ).fetchone()["avg"]

        # Status breakdown
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM applications GROUP BY status"
        ).fetchall()
        stats["status_breakdown"] = {r["status"]: r["cnt"] for r in rows}

        # Source breakdown
        rows = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source"
        ).fetchall()
        stats["source_breakdown"] = {r["source"]: r["cnt"] for r in rows}

        # Top matching companies
        rows = conn.execute("""
            SELECT j.company, AVG(a.match_score) as avg_score, COUNT(*) as cnt
            FROM applications a JOIN jobs j ON a.job_id = j.id
            GROUP BY j.company ORDER BY avg_score DESC LIMIT 10
        """).fetchall()
        stats["top_companies"] = [dict(r) for r in rows]

        conn.close()
        return stats
