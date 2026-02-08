"""
Database connection and pooling
"""

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2 import pool
import logging
import os

logger = logging.getLogger(__name__)

# Database connection pool
connection_pool = None


def init_connection_pool():
    """Initialize database connection pool"""
    global connection_pool
    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            host='127.0.0.1',
            port=5432,
            database='olympics_tv',
            user='stosh99',
            password='olympics_tv_dev'
        )
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {e}")
        raise


def get_connection():
    """Get a connection from the pool"""
    if not connection_pool:
        init_connection_pool()
    return connection_pool.getconn()


def return_connection(conn):
    """Return a connection to the pool"""
    if connection_pool:
        connection_pool.putconn(conn)


def close_all_connections():
    """Close all connections in the pool"""
    if connection_pool:
        connection_pool.closeall()


def execute_query(query, params=None):
    """Execute a query and return results"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        return results
    finally:
        return_connection(conn)


def execute_query_dict(query, params=None):
    """Execute a query and return results as dictionaries"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # Get column names
        columns = [desc[0] for desc in cursor.description]

        # Fetch results
        rows = cursor.fetchall()
        cursor.close()

        # Convert to list of dicts
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))

        return results
    finally:
        return_connection(conn)
