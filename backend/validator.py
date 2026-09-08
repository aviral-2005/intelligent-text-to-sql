import re


FORBIDDEN_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
]


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate LLM-generated SQL before execution.

    Allows read-only SELECT queries, including CTEs starting with WITH.

    Returns:
        (True, "Valid SQL") if the query is safe.
        (False, reason) if the query should not be executed.
    """

    if not sql or not sql.strip():
        return False, "SQL query is empty."

    # Remove Markdown code fences if the LLM returned them.
    sql = re.sub(
        r"```(?:sql)?\s*",
        "",
        sql,
        flags=re.IGNORECASE,
    )
    sql = sql.replace("```", "").strip()

    # Remove leading SQL comments.
    # Handles both:
    #   -- comment
    #   /* comment */
    sql = re.sub(
        r"^\s*(?:(?:--[^\n]*\n)|(?:/\*.*?\*/\s*))+",
        "",
        sql,
        flags=re.DOTALL,
    ).strip()

    if not sql:
        return False, "SQL query is empty."

    # Only allow read-only SELECT queries.
    # WITH is allowed because PostgreSQL CTE queries commonly start with WITH.
    if not re.match(r"^(SELECT|WITH)\b", sql, re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    # Reject multiple SQL statements.
    # A single trailing semicolon is allowed.
    statements = sql.rstrip().rstrip(";").strip()

    if ";" in statements:
        return False, "Multiple SQL statements are not allowed."

    # Check for destructive/modifying SQL commands.
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql, re.IGNORECASE):
            return False, f"Forbidden SQL keyword detected: {keyword}"

    return True, "Valid SQL"