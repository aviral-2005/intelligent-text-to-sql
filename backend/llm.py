import os
from dotenv import load_dotenv
from groq import Groq

from backend.schema import get_database_schema
from backend.models import SQLResponse


load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-120b"


def generate_sql(question: str) -> SQLResponse:
    schema = get_database_schema()

    prompt = f"""
You are a PostgreSQL Text-to-SQL expert.

Your job is to determine whether the user's question is clear enough
to generate a SQL query.

Database schema:
{schema}

Rules:

1. If the question is clear and can be answered using the database:
   - Set status to "ready"
   - Generate the PostgreSQL SQL query
   - Set clarification_question to null

2. If the question is ambiguous or missing important information:
   - Set status to "clarification_needed"
   - Set sql to null
   - Ask one concise clarification question

3. Do not guess the user's intended meaning when multiple reasonable
   interpretations exist.

4. Only generate SELECT queries.

5. Use only tables and columns present in the database schema.

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
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "sql_response",
                "schema": SQLResponse.model_json_schema()
            }
        }
    )

    content = response.choices[0].message.content

    return SQLResponse.model_validate_json(content)

def generate_sql_from_clarification(
    original_question: str,
    clarification_answer: str
) -> SQLResponse:

    schema = get_database_schema()

    prompt = f"""
You are a PostgreSQL Text-to-SQL expert.

The user originally asked:

{original_question}

The system asked for clarification.

The user's clarification answer was:

{clarification_answer}

Use the clarification answer to resolve the original question.

Database schema:
{schema}

Rules:

1. Generate the SQL that answers the original question
   using the clarification provided by the user.

2. Set status to "ready" if the clarification is sufficient.

3. If the clarification is still insufficient or ambiguous,
   set status to "clarification_needed" and ask one concise
   clarification question.

4. Only generate SELECT queries.

5. Use only tables and columns present in the database schema.

Return the structured response.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "sql_response",
                "schema": SQLResponse.model_json_schema()
            }
        }
    )

    content = response.choices[0].message.content

    return SQLResponse.model_validate_json(content)