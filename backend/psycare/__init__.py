"""Project package init.

On Windows, mysqlclient build may be unavailable. If PyMySQL is installed,
register it as a drop-in MySQLdb driver.
"""

try:
    import pymysql

    pymysql.install_as_MySQLdb()
except Exception:
    # Keep default mysqlclient path when available.
    pass
