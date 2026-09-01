from sqlalchemy import inspect
from backend.database import engine


def get_database_schema():
    inspector = inspect(engine)

    schema = []

    for table_name in inspector.get_table_names():

        # Get columns
        columns = inspector.get_columns(table_name)

        # Get primary key
        primary_key = inspector.get_pk_constraint(table_name)
        primary_key_columns = primary_key.get("constrained_columns", [])

        # Get foreign keys
        foreign_keys = inspector.get_foreign_keys(table_name)

        table_info = {
            "table": table_name,

            "columns": [
                {
                    "name": column["name"],
                    "type": str(column["type"])
                }
                for column in columns
            ],

            "primary_key": primary_key_columns,

            "foreign_keys": [
                {
                    "column": fk["constrained_columns"],
                    "references_table": fk["referred_table"],
                    "references_column": fk["referred_columns"]
                }
                for fk in foreign_keys
            ]
        }

        schema.append(table_info)

    return schema