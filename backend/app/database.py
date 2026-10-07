# SQLite 连接与初始化（单文件数据库，演示场景够用）
import os
import sqlite3

from . import config

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('super_admin','admin','operator','readonly')),
    data_scope TEXT NOT NULL DEFAULT 'self_only'
        CHECK(data_scope IN ('all','own_dept','own_team','self_only')),
    employee_id INTEGER,
    allowed_tables TEXT,          -- JSON 数组，为空表示不限
    allowed_columns TEXT,         -- JSON {表:[字段]}，为空表示不限
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    gender TEXT,
    birth_year INTEGER,
    department TEXT NOT NULL,
    sub_department TEXT,
    position TEXT,
    level TEXT,
    manager_id INTEGER REFERENCES employee(id),
    hire_date TEXT,
    education TEXT,
    phone TEXT,
    email TEXT,
    id_card_area TEXT,
    political_status TEXT,
    marital_status TEXT,
    children_count INTEGER DEFAULT 0,
    hometown TEXT,
    address TEXT,
    work_status TEXT DEFAULT '在职',
    contract_type TEXT,
    entry_channel TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS salary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id INTEGER NOT NULL REFERENCES employee(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    base_pay REAL NOT NULL,
    bonus REAL DEFAULT 0,
    gross_pay REAL NOT NULL,
    UNIQUE(emp_id, year, month)
);

CREATE TABLE IF NOT EXISTS attendance_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id INTEGER NOT NULL REFERENCES employee(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    work_days INTEGER DEFAULT 0,
    overtime_hours REAL DEFAULT 0,
    leave_days REAL DEFAULT 0,
    late_count INTEGER DEFAULT 0,
    UNIQUE(emp_id, year, month)
);

CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id INTEGER NOT NULL REFERENCES employee(id),
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    kpi_score REAL,
    rating TEXT,
    UNIQUE(emp_id, year, quarter)
);

CREATE TABLE IF NOT EXISTS query_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    question TEXT NOT NULL,
    model TEXT,
    sql TEXT,
    row_count INTEGER DEFAULT 0,
    chart_type TEXT,
    elapsed_ms INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'success',
    error_msg TEXT,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS question_template (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name TEXT NOT NULL,
    title TEXT NOT NULL,
    question TEXT NOT NULL,
    sql TEXT NOT NULL,
    chart_type TEXT NOT NULL DEFAULT 'table',
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    username TEXT,
    action TEXT NOT NULL,
    detail TEXT,
    ip TEXT,
    elapsed_ms INTEGER DEFAULT 0,
    result TEXT NOT NULL DEFAULT '成功',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_username ON audit_log(username);
CREATE INDEX IF NOT EXISTS idx_history_user ON query_history(user_id, created_at DESC);
"""


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """建表（幂等）。数据灌入由 seed.py 负责。"""
    conn = get_conn()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
