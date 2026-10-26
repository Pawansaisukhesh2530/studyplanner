"""The real application's database. No sample records are inserted here."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3


DATA_FOLDER = Path(__file__).resolve().parents[1] / "data"
DATABASE_FILE = DATA_FOLDER / "student_growth.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY COLLATE NOCASE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('faculty', 'student')),
    password_hash TEXT NOT NULL,
    must_change_password INTEGER NOT NULL DEFAULT 1,
    interests TEXT NOT NULL DEFAULT '',
    goals TEXT NOT NULL DEFAULT '',
    weekly_hours REAL NOT NULL DEFAULT 3
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    username TEXT NOT NULL REFERENCES users(username),
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS courses (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    pass_percentage REAL NOT NULL CHECK(pass_percentage BETWEEN 0 AND 100)
);
CREATE TABLE IF NOT EXISTS enrolments (
    student_id TEXT NOT NULL REFERENCES users(username),
    course_code TEXT NOT NULL REFERENCES courses(code),
    PRIMARY KEY(student_id, course_code)
);
CREATE TABLE IF NOT EXISTS marks (
    id INTEGER PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES users(username),
    course_code TEXT NOT NULL REFERENCES courses(code),
    assessment TEXT NOT NULL,
    assessment_date TEXT NOT NULL,
    score REAL NOT NULL,
    max_score REAL NOT NULL,
    CHECK(max_score > 0 AND score >= 0 AND score <= max_score),
    UNIQUE(student_id, course_code, assessment, assessment_date)
);
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY,
    course_code TEXT NOT NULL REFERENCES courses(code),
    title TEXT NOT NULL,
    instructions TEXT NOT NULL,
    due_date TEXT NOT NULL,
    created_by TEXT NOT NULL REFERENCES users(username)
);
CREATE TABLE IF NOT EXISTS assignment_status (
    assignment_id INTEGER NOT NULL REFERENCES assignments(id),
    student_id TEXT NOT NULL REFERENCES users(username),
    completed_at TEXT,
    PRIMARY KEY(assignment_id, student_id)
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES users(username),
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open', 'Done'))
);
CREATE TABLE IF NOT EXISTS clubs (
    club_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    interests TEXT NOT NULL,
    goals TEXT NOT NULL,
    skills TEXT NOT NULL,
    hours_per_week REAL NOT NULL CHECK(hours_per_week > 0),
    example_activities TEXT NOT NULL,
    potential_benefit TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memberships (
    student_id TEXT NOT NULL REFERENCES users(username),
    club_id TEXT NOT NULL REFERENCES clubs(club_id),
    status TEXT NOT NULL CHECK(status IN ('Interested', 'Participating')),
    PRIMARY KEY(student_id, club_id)
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    club_id TEXT NOT NULL REFERENCES clubs(club_id),
    title TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    location TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES users(username),
    title TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES users(username),
    club_id TEXT NOT NULL REFERENCES clubs(club_id),
    event_id INTEGER REFERENCES events(id),
    activity_date TEXT NOT NULL,
    description TEXT NOT NULL,
    hours REAL NOT NULL CHECK(hours > 0 AND hours <= 24),
    skills_practised TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    recorded_at TEXT NOT NULL,
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    record_key TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS college_holidays (
    holiday_date TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
INSERT OR IGNORE INTO app_meta(key, value) VALUES ('schema_version', '2');
"""


@contextmanager
def open_database(database_file=DATABASE_FILE):
    path = Path(database_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(database_file=DATABASE_FILE):
    with open_database(database_file) as database:
        database.executescript(SCHEMA)


def rows(database, sql, parameters=()):
    return [dict(row) for row in database.execute(sql, parameters).fetchall()]
