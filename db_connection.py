"""Centralized database connection management with connection pooling."""

import mysql.connector
from mysql.connector import pooling
import os


class DatabaseConnection:
    _pool = None

    @classmethod
    def get_pool(cls):
        if cls._pool is None:
            cls._pool = pooling.MySQLConnectionPool(
                pool_name="pubg_pool",
                pool_size=5,
                host=os.getenv("DB_HOST", "localhost"),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", ""),
                database=os.getenv("DB_NAME", "pubg"),
            )
        return cls._pool

    @classmethod
    def get_connection(cls):
        return cls.get_pool().get_connection()

    @classmethod
    def execute_query(cls, query, params=None, fetch=True):
        conn = cls.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            if fetch:
                return cursor.fetchall()
            conn.commit()
            return cursor.rowcount
        finally:
            cursor.close()
            conn.close()
