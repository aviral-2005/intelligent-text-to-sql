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

    Returns:
        (True, "Valid SQL") if the query is safe.
        (False, reason) if the query should not be executed.
    """

    if not sql or not sql.strip():
        return False, "SQL query is empty."

    # Remove Markdown code fences if the LLM returned them
    sql = re.sub(r"```(?:sql)?", "", sql, flags=re.IGNORECASE)
    sql = sql.replace("```", "").strip()

    # Only allow SELECT queries for now
    if not re.match(r"^SELECT\b", sql, re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    # Check for destructive/modifying SQL commands
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql, re.IGNORECASE):
            return False, f"Forbidden SQL keyword detected: {keyword}"

    return True, "Valid SQL"