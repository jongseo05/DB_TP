# db.py
import mysql.connector
from mysql.connector import errors as mysql_errors

# optional fallback driver
try:
    import pymysql
    from pymysql.cursors import DictCursor
except Exception:
    pymysql = None


def get_db():
    """Return a DB connection.

    Tries to use mysql.connector first. If the server requires an
    authentication plugin not supported by mysql.connector (e.g.
    caching_sha2_password), and PyMySQL is installed, falls back to PyMySQL.

    If neither works, raises a clear RuntimeError with remediation steps.
    """
    # connection params (move to env vars if needed)
    cfg = dict(
        host="localhost",
        user="root",
        password="9799",
        database="youtube_app",
    )

    try:
        conn = mysql.connector.connect(**cfg)
        driver = "mysqlconnector"
    except mysql_errors.NotSupportedError:
        # common cause: server uses caching_sha2_password which this
        # mysql.connector installation doesn't support.
        if pymysql is None:
            raise RuntimeError(
                "MySQL server requires 'caching_sha2_password' auth plugin which is not supported by the installed mysql-connector-python.\n"
                "Options:\n"
                "  1) Install PyMySQL in this environment: python -m pip install pymysql\n"
                "  2) Or change the MySQL user to use mysql_native_password on the server:\n"
                "     ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your_password';\n"
                "     FLUSH PRIVILEGES;"
            )

        # fallback using PyMySQL (use DictCursor so callers get dict rows)
        conn = pymysql.connect(cursorclass=DictCursor, db=cfg["database"], **{k: v for k, v in cfg.items() if k != "database"})
        driver = "pymysql"

    # Wrap connection to provide a compatible cursor(dictionary=True) signature
    class _ConnWrapper:
        def __init__(self, conn, driver):
            self._conn = conn
            self._driver = driver

        def cursor(self, *args, **kwargs):
            # support `dictionary=True` used by mysql.connector code
            if kwargs.pop("dictionary", False):
                if self._driver == "mysqlconnector":
                    return self._conn.cursor(dictionary=True)
                else:
                    # pymysql uses DictCursor via cursorclass; ignore kw
                    return self._conn.cursor(*args, **kwargs)
            return self._conn.cursor(*args, **kwargs)

        def close(self):
            return self._conn.close()

        def commit(self):
            return self._conn.commit()

        def rollback(self):
            return self._conn.rollback()

        def __getattr__(self, item):
            return getattr(self._conn, item)
        
        def get_raw_connection(self):
            """Return the raw connection for pandas or other libraries."""
            return self._conn

    return _ConnWrapper(conn, driver)
