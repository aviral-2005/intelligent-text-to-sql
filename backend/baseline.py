import os

from dotenv import load_dotenv
from groq import Groq

from backend.schema import get_database_schema
from backend.models import BaselineSQLResponse

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-120b"


def generate_baseline_sql(question: str) -> BaselineSQLResponse:
    """
    Generate SQL using the baseline approach.

    The baseline must always attempt to generate SQL.
    It does not ask the user for clarification.
    """

    schema = get_database_schema()

    prompt = f"""
You are a PostgreSQL Text-to-SQL expert.

Your job is to convert the user's natural-language question
into a PostgreSQL SQL query.

Database schema:
{schema}

Rules:

1. Always attempt to answer the user's question.
2. NEVER ask for clarification.
3. If the question is ambiguous, make the most reasonable
   interpretation and generate SQL.
4. Only generate SELECT queries.
5. Use only tables and columns present in the database schema.
6. Return only the SQL query when the question can be answered.
7. Do not invent tables or columns.

User question:
{question}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "baseline_sql_response",
                "schema": BaselineSQLResponse.model_json_schema()
            }
        }
    )

    content = response.choices[0].message.content

    return BaselineSQLResponse.model_validate_json(content)