"""
One-time DB migration: adds missing columns to the student_user table.
Safe to run multiple times — skips columns that already exist.
"""
import sqlite3, os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')

if not os.path.exists(db_path):
    print(f"[INFO] Database not found at {db_path}. Nothing to migrate.")
else:
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    cur.execute("PRAGMA table_info(student_user)")
    existing_cols = {row[1] for row in cur.fetchall()}
    print(f"[INFO] Existing student_user columns: {existing_cols}")

    migrations = [
        ("plain_dob",    "ALTER TABLE student_user ADD COLUMN plain_dob    TEXT"),
        ("student_name", "ALTER TABLE student_user ADD COLUMN student_name TEXT"),
        ("student_sem",  "ALTER TABLE student_user ADD COLUMN student_sem  TEXT"),
        ("s_year",       "ALTER TABLE student_user ADD COLUMN s_year       TEXT"),
    ]

    for col_name, sql in migrations:
        if col_name not in existing_cols:
            cur.execute(sql)
            print(f"[OK]   Added column: student_user.{col_name}")
        else:
            print(f"[SKIP] Column already exists: student_user.{col_name}")

    # Also fix quiz_result if needed
    cur.execute("PRAGMA table_info(quiz_result)")
    qr_cols = {row[1] for row in cur.fetchall()}
    print(f"[INFO] Existing quiz_result columns: {qr_cols}")

    qr_migrations = [
        ("dailyTime", "ALTER TABLE quiz_result ADD COLUMN dailyTime TEXT"),
        ("history",   "ALTER TABLE quiz_result ADD COLUMN history   TEXT"),
    ]
    for col_name, sql in qr_migrations:
        if col_name not in qr_cols:
            cur.execute(sql)
            print(f"[OK]   Added column: quiz_result.{col_name}")
        else:
            print(f"[SKIP] Column already exists: quiz_result.{col_name}")

    conn.commit()
    conn.close()
    print("\n[DONE] Migration complete.")
