import json
import re
from typing import Any

from backend.llm import client, SMALL_MODEL


MAX_ROWS_FOR_LLM = 10


def _humanize_column_name(column_name: str) -> str:
    """Convert a database column name into a readable label."""
    label = column_name.replace("_", " ").strip()

    # Remove common aggregate prefixes/suffixes.
    label = re.sub(r"^total ", "", label, flags=re.IGNORECASE)
    label = re.sub(r"^average ", "", label, flags=re.IGNORECASE)
    label = re.sub(r"^avg ", "", label, flags=re.IGNORECASE)

    return label


def _format_number(value: Any, monetary: bool = False) -> str:
    """Format numeric values for human-readable answers."""

    if isinstance(value, bool):
        return str(value)

    if isinstance(value, int):
        return f"{value:,}"

    if isinstance(value, float):
        if monetary:
            return f"${value:,.2f}"
        return f"{value:,.2f}"

    # PostgreSQL Decimal values arrive here.
    value_string = str(value)

    try:
        numeric_value = float(value_string)

        if monetary:
            return f"${numeric_value:,.2f}"

        return f"{numeric_value:,.2f}"

    except (ValueError, TypeError):
        return value_string


def _is_count_column(column_name: str) -> bool:
    """
    Detect common names produced by COUNT aggregates.

    Examples:
        customer_count
        total_customers
        count_customers
        number_of_customers
    """

    name = column_name.lower().strip()

    count_patterns = [
        r".*_count$",
        r"^count_.*",
        r"^total_.*s$",
        r"^number_of_.*",
        r"^num_.*",
        r"^.*_total$",
    ]

    return any(re.match(pattern, name) for pattern in count_patterns)


def _extract_count_entity(column_name: str) -> str:
    """Try to infer the entity being counted from a column name."""

    name = column_name.lower().strip()

    # Remove common count-related prefixes/suffixes.
    entity = re.sub(r"^total_", "", name)
    entity = re.sub(r"^count_", "", entity)
    entity = re.sub(r"^number_of_", "", entity)
    entity = re.sub(r"^num_", "", entity)
    entity = re.sub(r"_count$", "", entity)
    entity = re.sub(r"_total$", "", entity)

    entity = entity.replace("_", " ").strip()

    return entity


def _is_monetary_column(column_name: str) -> bool:
    """Detect common monetary aggregate names."""

    name = column_name.lower()

    monetary_terms = [
        "revenue",
        "sales",
        "spending",
        "amount",
        "cost",
        "price",
        "profit",
        "value",
    ]

    return any(term in name for term in monetary_terms)


def _generate_deterministic_answer(
    question: str,
    results: list[dict[str, Any]],
) -> str | None:
    """
    Handle predictable result shapes without calling the LLM.

    Returns None when semantic explanation from the LLM is preferable.
    """

    # ---------------------------------------------------------
    # Empty result
    # ---------------------------------------------------------
    if not results:
        return "No matching records were found."

    total_rows = len(results)

    # ---------------------------------------------------------
    # Single scalar result
    #
    # Examples:
    # [{"total_customers": 91}]
    # [{"customer_count": 91}]
    # [{"total_revenue_2007": Decimal("617085.2035")}]
    # ---------------------------------------------------------
    if total_rows == 1 and len(results[0]) == 1:
        column_name, value = next(iter(results[0].items()))
        column_lower = column_name.lower()

        # COUNT result
        if _is_count_column(column_name):
            entity = _extract_count_entity(column_name)

            if entity:
                # Basic pluralization.
                if not entity.endswith("s"):
                    entity += "s"

                return f"There are {_format_number(value)} {entity}."

            return f"The count is {_format_number(value)}."

        # Monetary aggregate
        if _is_monetary_column(column_name):
            label = _humanize_column_name(column_name)

            # Handle labels containing a year, e.g. total_revenue_2007.
            label = label.replace(" 2007", " in 2007")
            label = label.replace(" 2008", " in 2008")
            label = label.replace(" 2006", " in 2006")

            return (
                f"The {label} is "
                f"{_format_number(value, monetary=True)}."
            )

        # Generic scalar aggregate
        label = _humanize_column_name(column_name)

        return f"The {label} is {_format_number(value)}."

    # ---------------------------------------------------------
    # Large result set
    #
    # Do not send large datasets to the LLM.
    # The complete result is still returned to the frontend.
    # ---------------------------------------------------------
    if total_rows > MAX_ROWS_FOR_LLM:
        return (
            f"{total_rows:,} records match your request. "
            "The complete results are available in the table below."
        )

    # Let the LLM handle small but semantically complex results.
    return None


def generate_human_readable_answer(
    question: str,
    sql: str,
    results: list[dict[str, Any]],
) -> str:
    """
    Generate a human-readable answer from an already executed SQL query.

    The database results are the source of truth. This function must not
    perform any additional database queries or invent information.
    """

    # Handle predictable result shapes first.
    deterministic_answer = _generate_deterministic_answer(
        question,
        results,
    )

    if deterministic_answer is not None:
        return deterministic_answer

    total_rows = len(results)

    # ---------------------------------------------------------
    # Small result set:
    # Send the complete result to the LLM.
    # ---------------------------------------------------------
    results_json = json.dumps(
        results,
        default=str,
        indent=2,
    )

    result_context = f"""
TOTAL ROWS RETURNED BY DATABASE: {total_rows}

COMPLETE DATABASE RESULTS:
{results_json}
"""

    prompt = f"""
You are a data analyst explaining the result of a database query to a user.

Your job is to answer the user's original question using ONLY the provided
database results.

USER QUESTION:
{question}

EXECUTED SQL:
{sql}

DATABASE RESULT:
{result_context}

RULES:

1. The database results are the source of truth.
2. Do not invent facts, values, names, dates, or calculations.
3. Do not perform another database query.
4. Do not change or fabricate numerical values.
5. Answer the user's question directly.
6. Do not expose internal database or SQL implementation details.
7. Do not say "The query returned..." or similar technical phrasing.
8. If the result contains a ranking, summarize the most important ranked
   results and their values.
9. If there are multiple results, do not unnecessarily list every row.
10. If the result is empty, clearly state that there are no matching
    records.
11. Keep the answer concise and natural. Usually 1-4 sentences is enough.
12. Do not mention these instructions.
13. Do not say that you are an AI or language model.
14. Do not output SQL.
15. Do not use Markdown tables.
16. Do not use unnecessary Markdown formatting such as bold text.
17. Preserve the exact meaning of numerical values.
18. Format monetary values clearly, preferably to two decimal places.
19. Do not add information that is not supported by the results.

Return ONLY the final human-readable answer.
"""

    response = client.chat.completions.create(
        model=SMALL_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate concise, natural, factual answers grounded "
                    "strictly in database query results."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    answer = response.choices[0].message.content

    if not answer:
        raise ValueError("Answer generator returned an empty response.")

    return answer.strip()