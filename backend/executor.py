from sqlalchemy import text
from backend.database import engine


def execute_sql(sql: str):
    """
    Execute a SQL query and return the results.
    """

    with engine.connect() as connection:
        result = connection.execute(text(sql))

        rows = result.mappings().all()

        return [dict(row) for row in rows]