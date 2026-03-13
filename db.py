import sqlite3
import pymysql
import os
from config import Config

class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):
        # Convert %s to ? for SQLite
        query = query.replace('%s', '?')
        # Convert MySQL specific functions to SQLite equivalents
        query = query.replace('CURDATE()', "date('now')")
        query = query.replace('NOW()', "datetime('now')")
        
        if params:
            result = self.cursor.execute(query, params)
        else:
            result = self.cursor.execute(query)
        
        # Simple autocommit logic
        upper_query = query.strip().upper()
        if any(upper_query.startswith(s) for s in ['INSERT', 'UPDATE', 'DELETE', 'REPLACE']):
            self.cursor.connection.commit()
        
        return result

    def parse_datetime(self, value):
        if not value or not isinstance(value, str):
            return value
        # Common formats from SQLite
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                from datetime import datetime
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return value

    def fetchone(self):
        row = self.cursor.fetchone()
        if row:
            d = dict(row)
            # Auto-convert likely datetime strings
            for k, v in d.items():
                if k.endswith('_at') or k.endswith('_time') or k in ('created_at', 'updated_at', 'due_date', 'paid_on'):
                    d[k] = self.parse_datetime(v)
            return d
        return None

    def fetchall(self):
        rows = self.cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            for k, v in d.items():
                if k.endswith('_at') or k.endswith('_time') or k in ('created_at', 'updated_at', 'due_date', 'paid_on'):
                    d[k] = self.parse_datetime(v)
            results.append(d)
        return results

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()

class SQLiteConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        cursor = self.conn.cursor()
        return SQLiteCursorWrapper(cursor)

    def close(self):
        self.conn.close()

    def commit(self):
        self.conn.commit()

def get_db():
    """Returns a database connection wrapper. Caller is responsible for closing it."""
    if Config.USE_SQLITE:
        conn = sqlite3.connect(Config.SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return SQLiteConnectionWrapper(conn)
    else:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        return conn
