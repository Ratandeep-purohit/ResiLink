import sqlite3
import pymysql
import os
import re
from config import Config

def migrate():
    # Load schema
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if not os.path.exists(schema_path):
        print(f"Error: {schema_path} not found.")
        return

    with open(schema_path, 'r') as f:
        sql = f.read()

    try:
        if Config.USE_SQLITE:
            print("Migrating to SQLite...")
            sqlite_sql = sql
            
            # Basic conversion from MySQL to SQLite
            # Remove MySQL specific DB commands
            sqlite_sql = re.sub(r"(?i)CREATE DATABASE[^;]+;", "", sqlite_sql)
            sqlite_sql = re.sub(r"(?i)USE [^;]+;", "", sqlite_sql)
            
            # Replacements for SQLite compatibility
            sqlite_sql = sqlite_sql.replace('AUTO_INCREMENT', '')
            sqlite_sql = re.sub(r"(?i)\bINT\b", "INTEGER", sqlite_sql)
            sqlite_sql = sqlite_sql.replace('TINYINT(1)', 'INTEGER')
            sqlite_sql = sqlite_sql.replace('DECIMAL(10, 2)', 'REAL')
            sqlite_sql = sqlite_sql.replace('ON UPDATE CURRENT_TIMESTAMP', '')
            sqlite_sql = re.sub(r"(?i)ENUM\([^)]+\)", "VARCHAR(50)", sqlite_sql)
            sqlite_sql = sqlite_sql.replace('INSERT IGNORE', 'INSERT OR IGNORE')

            conn = sqlite3.connect(Config.SQLITE_DB_PATH)
            try:
                conn.executescript(sqlite_sql)
                conn.commit()
                print(f"SQLite database initialized at {Config.SQLITE_DB_PATH}")
            finally:
                conn.close()
        else:
            print(f"Migrating to MySQL ({Config.DB_NAME} at {Config.DB_HOST})...")
            conn = pymysql.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                autocommit=True
            )
            with conn.cursor() as cur:
                statements = re.split(r';\s*(?=\n|$)', sql)
                for statement in statements:
                    stmt = statement.strip()
                    if stmt:
                        if stmt.startswith('--') or stmt.startswith('/*'):
                            lines = [l for l in stmt.split('\n') if not l.strip().startswith('--')]
                            if not any(lines): continue
                        cur.execute(stmt)
            print("MySQL database migrated successfully.")
    except Exception as e:
        import traceback
        print(f"Migration Error: {e}")
        traceback.print_exc()
    finally:
        if 'conn' in locals() and not isinstance(conn, sqlite3.Connection):
            try:
                conn.close()
            except:
                pass

if __name__ == "__main__":
    migrate()
