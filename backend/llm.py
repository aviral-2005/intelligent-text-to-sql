import os
from dotenv import load_dotenv
from groq import Groq
from backend.schema import get_database_schema

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-120b"


def generate_sql(question: str) -> str:
    schema = get_database_schema()

    prompt = f"""
You are a PostgreSQL SQL expert.

Convert the user's natural language question into a PostgreSQL SQL query.

Database schema:
{schema}

Rules:
- Use only tables and columns present in the schema.
- Return only the SQL query.
- Do not use INSERT, UPDATE, DELETE, DROP, ALTER, or other destructive operations.

User question:
{question}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
    )

    sql = response.choices[0].message.content

    return sql